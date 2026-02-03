import logging
from datetime import datetime
import requests

DEFAULT_FETCH_LIMIT = 100  # maximum commits per page supported by API

logger = logging.getLogger(__name__)


def _build_api_base(base_url: str, api_version: str) -> str:
    trimmed = base_url.rstrip("/")
    if "/rest/api/" in trimmed:
        trimmed = trimmed.split("/rest/api/")[0]
    return f"{trimmed}/rest/api/{api_version}"


def resolve_bitbucket_base_url(bitbucket_base_url, bitbucket_auth, bitbucket_headers):
    candidates = [
        _build_api_base(bitbucket_base_url, "1.0"),
        _build_api_base(bitbucket_base_url, "latest"),
    ]
    for candidate in candidates:
        try:
            response = requests.get(
                f"{candidate}/projects",
                auth=bitbucket_auth,
                headers=bitbucket_headers,
                params={"limit": 1},
                timeout=10,
            )
            if response.ok:
                if candidate != bitbucket_base_url:
                    logger.info("Using Bitbucket API base URL %s", candidate)
                return candidate
            logger.warning(
                "Bitbucket API base URL %s returned %s. Response: %s",
                candidate,
                response.status_code,
                response.text[:200],
            )
        except requests.exceptions.RequestException as exc:
            logger.warning(
                "Bitbucket API base URL %s is unreachable. Check VPN/SSO or URL. Error: %s",
                candidate,
                exc,
            )
    return bitbucket_base_url


def fetch_commits(
    bitbucket_base_url,
    repo_name,
    branch,
    bitbucket_auth,
    bitbucket_headers,
    limit: int = DEFAULT_FETCH_LIMIT,
    start_date=None,
    end_date=None,
):
    """
    Fetch commits from a Bitbucket Server repository for a specific branch within a date range.
    
    Args:
        bitbucket_base_url (str): Base URL of Bitbucket Server API.
        repo_name (str): Repository name (e.g., 'STARSYSONE/claimcenter').
        branch (str): Branch name (e.g., 'develop').
        bitbucket_auth (tuple): Authentication tuple (email, token).
        bitbucket_headers (dict): Request headers.
        limit (int): Number of commits per page.
        start_date (datetime): Start of date range (inclusive).
        end_date (datetime): End of date range (inclusive).
    
    Returns:
        list: List of commit objects.
    """
    # Extract project and repo from repo_name
    try:
        project, repo = repo_name.split('/')
    except ValueError:
        logger.error(f"Invalid repo_name format: {repo_name}. Expected 'PROJECT/REPO'.")
        raise ValueError(f"Invalid repo_name: {repo_name}")

    commits_url = f"{bitbucket_base_url}/projects/{project}/repos/{repo}/commits?at=refs/heads/{branch}"
    logger.debug(f"Fetching commits from {commits_url}")
    
    all_commits = []
    start = 0
    params = {"start": start, "limit": limit}

    while True:
        paginated_url = f"{commits_url}&start={start}&limit={limit}"
        try:
            response = requests.get(paginated_url, auth=bitbucket_auth, headers=bitbucket_headers, params=params)
            response.raise_for_status()
            commits = response.json()
            values = commits.get("values", [])
            
            # Filter commits by date range (client-side)
            filtered_commits = []
            for commit in values:
                commit_date = datetime.fromtimestamp(commit["authorTimestamp"] / 1000)
                if start_date and commit_date < start_date:
                    continue
                if end_date and commit_date > end_date:
                    continue
                filtered_commits.append(commit)
            
            all_commits.extend(filtered_commits)
            
            if commits.get("isLastPage", True):
                break
            start = commits.get("nextPageStart", start + limit)
            params["start"] = start
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch commits for {repo_name} branch {branch}: {str(e)}")
            raise
    
    logger.info(f"Total commits fetched for {repo_name} branch {branch}: {len(all_commits)}")
    return all_commits
