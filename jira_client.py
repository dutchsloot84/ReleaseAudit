import requests
import os
import logging
from jira_token_manager import get_valid_access_token

ACCESSIBLE_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"
DEFAULT_JIRA_SITE_URL = "https://csaaig.atlassian.net"

logger = logging.getLogger(__name__)


def discover_cloud_id(token: str, jira_site_url: str) -> str:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    response = requests.get(ACCESSIBLE_RESOURCES_URL, headers=headers)
    response.raise_for_status()
    resources = response.json()
    normalized_url = jira_site_url.rstrip("/")
    for resource in resources:
        if resource.get("url", "").rstrip("/") == normalized_url:
            return resource["id"]
    for resource in resources:
        scopes = resource.get("scopes", [])
        if any("jira" in scope for scope in scopes):
            return resource["id"]
    raise RuntimeError(f"No Jira site found for url {jira_site_url}")


def build_jira_api_base(cloud_id: str) -> str:
    return f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3"


def fetch_issues_by_jql(jql, token_file="jira_token.json", max_results=100):
    token = get_valid_access_token(token_file)
    jira_site_url = os.getenv("JIRA_SITE_URL", DEFAULT_JIRA_SITE_URL)
    cloud_id = discover_cloud_id(token, jira_site_url)
    jira_api_base = build_jira_api_base(cloud_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    response = requests.get(
        f"{jira_api_base}/search",
        headers=headers,
        params={
            "jql": jql,
            "maxResults": max_results,
            "fields": "key,summary,issuetype,fixVersions",
        },
    )
    if response.status_code in (401, 410):
        token = get_valid_access_token(token_file)
        if response.status_code == 410:
            cloud_id = discover_cloud_id(token, jira_site_url)
            jira_api_base = build_jira_api_base(cloud_id)
        headers["Authorization"] = f"Bearer {token}"
        response = requests.get(
            f"{jira_api_base}/search",
            headers=headers,
            params={
                "jql": jql,
                "maxResults": max_results,
                "fields": "key,summary,issuetype,fixVersions",
            },
        )
    response.raise_for_status()
    return response.json()["issues"]


def load_jira_issues(fix_version: str, token_file: str = "jira_token.json") -> dict:
    """Load Jira issues for the given fix version via the Jira Cloud REST API."""
    excluded_issue_types = [
        "Sub-task",
        "Tech Story",
        "Epic",
        "Test Execution",
        "Dev Task",
        "QA Task",
        "Shoulder Check",
        "Automation",
        "Test Plan",
        "Spike",
        "Test",
    ]
    issue_list = ", ".join(f'"{issue_type.strip()}"' for issue_type in excluded_issue_types)
    jql = f'fixVersion = "{fix_version}" AND issuetype not in ({issue_list})'

    token = get_valid_access_token(token_file)
    jira_site_url = os.getenv("JIRA_SITE_URL", DEFAULT_JIRA_SITE_URL)
    cloud_id = discover_cloud_id(token, jira_site_url)
    jira_api_base = build_jira_api_base(cloud_id)

    all_issues = []
    start_at = 0
    max_results = 100
    while True:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": "summary,issuetype,fixVersions,components,status",
        }
        response = requests.get(f"{jira_api_base}/search", headers=headers, params=params)
        if response.status_code in (401, 410):
            token = get_valid_access_token(token_file)
            if response.status_code == 410:
                cloud_id = discover_cloud_id(token, jira_site_url)
                jira_api_base = build_jira_api_base(cloud_id)
            headers["Authorization"] = f"Bearer {token}"
            response = requests.get(
                f"{jira_api_base}/search",
                headers=headers,
                params=params,
            )
        response.raise_for_status()
        data = response.json()
        all_issues.extend(data.get("issues", []))
        if start_at + max_results >= data.get("total", 0):
            break
        start_at += max_results

    jira_base = os.getenv("JIRA_BASE_URL", "https://csaaig.atlassian.net/browse")
    stories = {}
    for issue in all_issues:
        key = issue.get("key", "").upper()
        fields = issue.get("fields", {})
        stories[key] = {
            "Jira Story": key,
            "IssueType": fields.get("issuetype", {}).get("name", ""),
            "Summary": fields.get("summary", ""),
            "App": ", ".join(c.get("name", "") for c in fields.get("components", [])),
            "Status": fields.get("status", {}).get("name", ""),
            "FixVersion": ", ".join(v.get("name", "") for v in fields.get("fixVersions", [])),
            "Link": f"{jira_base.rstrip('/')}/{key}",
        }

    logger.info("Loaded %d Jira stories via API", len(stories))
    return stories
