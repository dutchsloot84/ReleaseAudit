import urllib.request
import urllib.parse
import json
import base64
import logging
import ssl
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

def fetch_jira_stories(jira_base_url, jql, auth, max_results=50, ca_bundle=None, threads=4):
    """Fetch Jira issues using JQL.

    The ``auth`` parameter can be either a tuple ``(email, token)`` for
    traditional Basic authentication or just a token string/tuple for Bearer
    token authentication.
    ``threads`` controls how many pages are fetched concurrently.
    """
    if not jira_base_url.endswith('/'):
        jira_base_url += '/'
    search_url = urllib.parse.urljoin(jira_base_url, 'rest/api/2/search')

    headers = {
        'Accept': 'application/json'
    }
    if isinstance(auth, tuple) and auth[0]:
        token_bytes = f"{auth[0]}:{auth[1]}".encode()
        headers['Authorization'] = 'Basic ' + base64.b64encode(token_bytes).decode()
    else:
        token = auth[1] if isinstance(auth, tuple) else auth
        headers['Authorization'] = f"Bearer {token}"

    context = ssl.create_default_context(cafile=ca_bundle) if ca_bundle else None

    def _fetch(params):
        url = search_url + '?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=context) as resp:
            return json.load(resp)

    # Fetch first page synchronously to determine total
    base_params = {
        'jql': jql,
        'startAt': 0,
        'maxResults': max_results,
        'fields': 'key,issuetype,summary,components,fixVersions'
    }
    try:
        first_page = _fetch(base_params)
    except Exception as e:
        logger.error(f"Failed to fetch Jira stories: {e}")
        raise

    issues = first_page.get('issues', [])
    total = first_page.get('total', len(issues))

    # Prepare parameters for remaining pages
    start_values = list(range(max_results, total, max_results))
    pages = []
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [
            executor.submit(_fetch, {**base_params, 'startAt': start})
            for start in start_values
        ]
        for fut in futures:
            try:
                data = fut.result()
                pages.append(data)
            except Exception as e:
                logger.error(f"Failed to fetch Jira page: {e}")
                raise

    for page in pages:
        issues.extend(page.get('issues', []))

    logger.info(f"Fetched {len(issues)} Jira stories from API")
    return issues


def map_jira_issues(issues):
    """Convert Jira issue JSON to internal story dictionary."""
    stories = {}
    for issue in issues:
        fields = issue.get('fields', {})
        key = issue.get('key')
        if not key:
            continue
        story = {
            'Jira_Story': key.upper(),
            'IssueType': fields.get('issuetype', {}).get('name', ''),
            'Summary': fields.get('summary', ''),
            'App': ','.join([c.get('name', '') for c in fields.get('components', [])]),
            'FixVersion': ','.join([v.get('name', '') for v in fields.get('fixVersions', [])]) or 'None',
            'Link': f"https://csaaig.atlassian.net/browse/{key}"
        }
        stories[story['Jira_Story']] = story
    return stories
