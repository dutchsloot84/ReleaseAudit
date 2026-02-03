import logging
import os
from typing import Iterable, Optional

import requests

from jira_token_manager import get_valid_access_token

ACCESSIBLE_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"
JIRA_API_ROOT = "https://api.atlassian.com/ex/jira"

logger = logging.getLogger(__name__)


def _normalize_site_url(site_url: Optional[str]) -> Optional[str]:
    if not site_url:
        return None
    normalized = site_url.rstrip("/")
    if normalized.endswith("/browse"):
        normalized = normalized[: -len("/browse")]
    return normalized


def get_accessible_resources(token: str) -> Iterable[dict]:
    response = requests.get(
        ACCESSIBLE_RESOURCES_URL,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    response.raise_for_status()
    return response.json()


def resolve_cloud_id(token: str, site_url: Optional[str] = None) -> str:
    normalized_site_url = _normalize_site_url(site_url)
    resources = list(get_accessible_resources(token))
    if not resources:
        raise RuntimeError("No accessible Jira resources found for this token.")

    if normalized_site_url:
        for resource in resources:
            resource_url = _normalize_site_url(resource.get("url"))
            if resource_url == normalized_site_url:
                return resource["id"]

    if len(resources) == 1:
        return resources[0]["id"]

    available = ", ".join(resource.get("url", "unknown") for resource in resources)
    raise RuntimeError(
        "Multiple Jira sites available. Set JIRA_SITE_URL to select the correct site. "
        f"Available sites: {available}"
    )


def build_jira_api_base(cloud_id: str) -> str:
    return f"{JIRA_API_ROOT}/{cloud_id}/rest/api/3"


def fetch_issues_by_jql(jql, token_file="jira_token.json", max_results=100):
    token = get_valid_access_token(token_file)
    site_url = os.getenv("JIRA_SITE_URL") or os.getenv("JIRA_BASE_URL")
    cloud_id = resolve_cloud_id(token, site_url=site_url)
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
    response.raise_for_status()
    return response.json()["issues"]


def load_jira_issues(fix_version: str, token_file: str = "jira_token.json") -> dict:
    """Load Jira issues for the given fix version via the Jira Cloud REST API."""
    issue_types = [
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
    issue_types = [issue_type.strip() for issue_type in issue_types]
    excluded_types = ", ".join(f'"{issue_type}"' for issue_type in issue_types)
    jql = (
        f'fixVersion = "{fix_version}" '
        f"AND issuetype not in ({excluded_types})"
    )

    token = get_valid_access_token(token_file)
    site_url = os.getenv("JIRA_SITE_URL") or os.getenv("JIRA_BASE_URL")
    cloud_id = resolve_cloud_id(token, site_url=site_url)
    jira_api_base = build_jira_api_base(cloud_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    all_issues = []
    start_at = 0
    max_results = 100
    for attempt in range(2):
        try:
            while True:
                params = {
                    "jql": jql,
                    "startAt": start_at,
                    "maxResults": max_results,
                    "fields": "summary,issuetype,fixVersions,components,status",
                }
                response = requests.get(
                    f"{jira_api_base}/search", headers=headers, params=params
                )
                response.raise_for_status()
                data = response.json()
                all_issues.extend(data.get("issues", []))
                if start_at + max_results >= data.get("total", 0):
                    break
                start_at += max_results
            break
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response else None
            if status_code in (401, 410) and attempt == 0:
                logger.warning(
                    "Jira API returned %s. Refreshing token and rediscovering site.",
                    status_code,
                )
                token = get_valid_access_token(token_file, force_refresh=True)
                headers["Authorization"] = f"Bearer {token}"
                cloud_id = resolve_cloud_id(token, site_url=site_url)
                jira_api_base = build_jira_api_base(cloud_id)
                all_issues = []
                start_at = 0
                continue
            raise

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
