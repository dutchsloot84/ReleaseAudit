import requests
import os
import logging
from jira_token_manager import get_valid_access_token

CLOUD_ID = "aaf3ee41-766b-44b8-8b12-92b0e035861f"
JIRA_API_BASE = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3"

logger = logging.getLogger(__name__)

def fetch_issues_by_jql(jql, token_file="jira_token.json", max_results=100):
    token = get_valid_access_token(token_file)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    response = requests.get(
        f"{JIRA_API_BASE}/search",
        headers=headers,
        params={
            "jql": jql,
            "maxResults": max_results,
            "fields": "key,summary,issuetype,fixVersions"
        }
    )
    response.raise_for_status()
    return response.json()["issues"]


def load_jira_issues(fix_version: str, token_file: str = "jira_token.json") -> dict:
    """Load Jira issues for the given fix version via the Jira Cloud REST API."""
    jql = (
        f'fixVersion = "{fix_version}" '
        'AND issuetype not in ('
        '"Sub-task", "Tech Story", "Epic", "Test Execution", '
        '"Dev Task", "QA Task", "Shoulder Check", "Automation ", '
        '"Test Plan", "Spike", "Test")'
    )

    token = get_valid_access_token(token_file)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    all_issues = []
    start_at = 0
    max_results = 100
    while True:
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": "summary,issuetype,fixVersions,components,status",
        }
        response = requests.get(f"{JIRA_API_BASE}/search", headers=headers, params=params)
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
