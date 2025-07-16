import urllib.request
import urllib.parse
import json
import base64
import logging
import ssl

logger = logging.getLogger(__name__)

def fetch_jira_stories(jira_base_url, jql, auth, max_results=50, ca_bundle=None):
    """Fetch Jira issues using JQL.

    The ``auth`` parameter can be either a tuple ``(email, token)`` for
    traditional Basic authentication or just a token string/tuple for Bearer
    token authentication.
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
    start_at = 0
    issues = []

    while True:
        params = {
            'jql': jql,
            'startAt': start_at,
            'maxResults': max_results,
            'fields': 'key,issuetype,summary,components,fixVersions'
        }
        url = search_url + '?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, context=context) as resp:
                data = json.load(resp)
        except Exception as e:
            logger.error(f"Failed to fetch Jira stories: {e}")
            raise
        issues.extend(data.get('issues', []))
        if start_at + max_results >= data.get('total', len(issues)):
            break
        start_at += max_results
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
