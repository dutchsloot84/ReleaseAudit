import os
import logging
import argparse
import pandas as pd
from datetime import datetime, timedelta
from config_loader import load_config
from bitbucket_api import fetch_commits
from commit_processor import extract_stories
from excel_writer import write_excel
from jira_api import fetch_jira_stories, map_jira_issues

# Logging setup
timestamp = datetime.now().strftime("%Y%m%d-%H%M")
log_filename = f"{timestamp}_gitxjira.log"
log_filepath = os.path.join(os.getcwd(), log_filename)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_filepath), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def get_config_value(env_var, config_key, config_dict, args, default=None):
    return (getattr(args, config_key, None) or
            os.environ.get(env_var) or
            config_dict.get(config_key) or
            default)


def main():
    parser = argparse.ArgumentParser(description="Compare Bitbucket commits with Jira stories fetched via JQL.")
    parser.add_argument('--develop-only', action='store_true', help='Only check the develop branch')
    parser.add_argument('--config', default='config.json', help='Path to config file')
    parser.add_argument('--jql', help='JQL query used to fetch Jira stories')
    parser.add_argument('--jira-base-url', help='Jira API base URL')
    parser.add_argument('--bitbucket-base-url', help='Bitbucket API base URL')
    parser.add_argument('--fix-version', help='Fix version for Jira stories')
    parser.add_argument('--release-branch', help='Release branch name')
    parser.add_argument('--develop-branch', help='Develop branch name')
    parser.add_argument('--test-range', action='store_true', help='Limit commit date range for testing')
    args = parser.parse_args()

    # Load configuration
    config_path = os.path.join(os.path.dirname(__file__), args.config)
    config = load_config(config_path)

    # Environment variables
    bitbucket_email = os.environ.get('BITBUCKET_EMAIL')
    bitbucket_token = os.environ.get('BITBUCKET_TOKEN')  # Personal Access Token
    jira_email = os.environ.get('JIRA_EMAIL')
    jira_token = os.environ.get('JIRA_TOKEN')
    required_vars = {
        'BITBUCKET_EMAIL': bitbucket_email,
        'BITBUCKET_TOKEN': bitbucket_token,
        'JIRA_EMAIL': jira_email,
        'JIRA_TOKEN': jira_token,
    }
    missing_vars = [key for key, value in required_vars.items() if not value]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    # Configuration values
    repos = config.get('repos', {
        "STARSYSONE/billingcenter": "BC", "STARSYSONE/policycenter": "PC",
        "STARSYSONE/claimcenter": "CC", "STARSYSONE/contactmanager": "CM"
    })
    fix_version = get_config_value('FIX_VERSION', 'fix_version', config, args, 'Mobilitas 2025.06.13')
    release_branch = get_config_value('RELEASE_BRANCH', 'release_branch', config, args, 'release/r-51.0')
    develop_branch = get_config_value('DEVELOP_BRANCH', 'develop_branch', config, args, 'develop')
    bitbucket_base_url = get_config_value('BITBUCKET_BASE_URL', 'bitbucket_base_url', config, args,
                                         'https://bitbucket.insu.dev-1.us-east-1.guidewire.net/rest/api/1.0')
    jira_base_url = get_config_value(
        'JIRA_BASE_URL',
        'jira_base_url',
        config,
        args,
        'https://api.atlassian.com/ex/jira/aaf3ee41-766b-44b8-8b12-92b0e035861f/rest/api/2/'
    )
    default_jql = (
        f'fixVersion = "{fix_version}" AND issuetype not in ('
        '"Sub-task", "Tech Story", "Epic", "Test Execution", "Dev Task", '
        '"QA Task", "Shoulder Check", "Automation ", "Test Plan", "Spike", "Test")'
    )
    jql = get_config_value('JQL', 'jql', config, args, default_jql)
    commit_fetch_limit = get_config_value('COMMIT_FETCH_LIMIT', 'commit_fetch_limit', config, args, 25)
    cutoff_days = get_config_value('CUTOFF_DAYS', 'cutoff_days_before_code_freeze', config, args, 28)
    code_freeze_days = get_config_value('CODE_FREEZE_DAYS', 'code_freeze_days_before_release', config, args, 17)

    # SSL configuration
    ca_bundle = r"C:\certs\csaa_netskope_combined.pem"
    use_ca_bundle = True  # Set to False if CA bundle fails

    # Authentication
    bitbucket_auth = (bitbucket_email, bitbucket_token)
    bitbucket_headers = {"Accept": "application/json"}
    jira_auth = (jira_email, jira_token)

    # Date calculations
    release_date = fix_version.replace("Mobilitas ", "")
    release_date_obj = datetime.strptime(release_date, "%Y.%m.%d")
    code_freeze_date = release_date_obj - timedelta(days=code_freeze_days)
    cutoff_date_obj = code_freeze_date - timedelta(days=cutoff_days) if not args.test_range else datetime.now() - timedelta(days=3)

    logger.info(f"Release Date: {release_date_obj.strftime('%Y-%m-%d')}")
    logger.info(f"Code Freeze Date: {code_freeze_date.strftime('%Y-%m-%d')}")
    logger.info(f"Cutoff Date: {cutoff_date_obj.strftime('%Y-%m-%d')}")

    # Output file
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    output_file = f"gitxjira_report_{timestamp}.xlsx"

    # Load Jira stories from API
    jira_issues = fetch_jira_stories(jira_base_url, jql, jira_auth, ca_bundle=ca_bundle if use_ca_bundle else None)
    jira_story_data = map_jira_issues(jira_issues)

    # Export Jira stories to Excel
    jira_df = pd.DataFrame(list(jira_story_data.values()))
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        jira_df.to_excel(writer, sheet_name="Jira Stories", index=False)
    logger.info(f"Exported Jira stories to {output_file} (Jira Stories sheet)")

    # Fetch and process commits
    all_commits = {}
    git_story_numbers = {}
    commit_hashes = {}
    branches = [develop_branch] if args.develop_only else [develop_branch, release_branch]

    for repo_name, app_name in repos.items():
        for branch in branches:
            logger.info(f"Fetching commits for {repo_name} ({app_name}) branch {branch}")
            try:
                commits = fetch_commits(
                    bitbucket_base_url,
                    repo_name,
                    branch,
                    bitbucket_auth,
                    bitbucket_headers,
                    commit_fetch_limit,
                    start_date=cutoff_date_obj,
                    end_date=code_freeze_date
                )
                logger.info(f"Fetched {len(commits)} commits for {repo_name} branch {branch}")
                filtered_commits = []
                for commit in commits:
                    extracted = extract_stories(
                        commit=commit,
                        fix_version=fix_version,
                        jira_story_data=jira_story_data,
                        app_name=app_name,
                        commit_hash=commit["id"],
                        branch=branch,
                        cutoff_date_obj=cutoff_date_obj,
                        code_freeze_date=code_freeze_date,
                        develop_branch=develop_branch,
                        git_story_numbers=git_story_numbers,
                        commit_hashes=commit_hashes,
                        exclude_patterns=[]
                    )
                    filtered_commits.extend(extracted)
                if filtered_commits:
                    all_commits.setdefault(app_name, []).extend(filtered_commits)
            except Exception as e:
                logger.error(f"Error fetching commits for {repo_name} branch {branch}: {str(e)}")

    # Identify missing Jira stories
    missing_from_git = [
        story for story in jira_story_data
        if story not in git_story_numbers
    ]
    missing_stories_data = [
        {
            "Jira Story": jira_story_data[story]["Jira_Story"],
            "Issue Type": jira_story_data[story]["IssueType"],
            "Summary": jira_story_data[story]["Summary"],
            "App": jira_story_data[story]["App"],
            "Fix Version": jira_story_data[story]["FixVersion"],
            "Link": jira_story_data[story]["Link"],
            "Missing From": "Git",
            "Notes": ""
        }
        for story in missing_from_git
    ]

    # Write commits and missing stories to Excel
    with pd.ExcelWriter(output_file, engine='openpyxl', mode='a') as writer:
        for app_name, commits in all_commits.items():
            df = pd.DataFrame(commits)
            df.to_excel(writer, sheet_name=app_name, index=False)
        if missing_stories_data:
            df_missing = pd.DataFrame(missing_stories_data)
            df_missing.to_excel(writer, sheet_name="Missing Jira Stories", index=False)

    logger.info(f"Generated report: {output_file}")

if __name__ == "__main__":
    main()
