import os
import logging
import argparse
import pandas as pd
from datetime import datetime, timedelta
from config_loader import load_config
from bitbucket_api import fetch_commits
from commit_processor import extract_stories
from excel_writer import write_excel

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

def load_jira_stories(csv_path):
    """Load JIRA stories from a CSV file."""
    try:
        df = pd.read_csv(csv_path)
        # Normalize column names (handle variations in JIRA export)
        df.columns = [col.strip().replace(' ', '_').lower() for col in df.columns]
        required_columns = ['key', 'issue_type', 'summary']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns in CSV: {', '.join(missing_columns)}")
        # Rename and select relevant columns
        stories = []
        for _, row in df.iterrows():
            story = {
                "Jira_Story": row['key'].strip().upper(),
                "Issue_Type": row['issue_type'],
                "Summary": row['summary'],
                "App": row.get('components', ''),
                "Fix_Version": row.get('fix_versions', 'None'),
                "Link": row.get('issue_link', f"https://csaaig.atlassian.net/browse/{row['key']}")
            }
            stories.append(story)
        logger.info(f"Loaded {len(stories)} Jira stories from {csv_path}")
        return {story["Jira_Story"]: story for story in stories}
    except Exception as e:
        logger.error(f"Failed to load Jira stories from {csv_path}: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Compare Bitbucket commits with Jira stories from CSV.")
    parser.add_argument('--develop-only', action='store_true', help='Only check the develop branch')
    parser.add_argument('--config', default='config.json', help='Path to config file')
    parser.add_argument('--jira-csv', default='jira_stories.csv', help='Path to Jira stories CSV file')
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
    required_vars = {
        'BITBUCKET_EMAIL': bitbucket_email,
        'BITBUCKET_TOKEN': bitbucket_token
    }
    missing_vars = [key for key, value in required_vars.items() if not value]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    # Configuration values
    repos = config.get('repos', {
        "STARSYSONE/billingcenter": "BC", "STARSYSONE/policycenter": "PC",
        "STARSYSONE/claimcenter": "CC", "STARSYSONE/contactmanager": "CM"
    })
    fix_version = get_config_value('FIX_VERSION', 'fix_version', config, args, 'Mobilitas 2025.04.18')
    release_branch = get_config_value('RELEASE_BRANCH', 'release_branch', config, args, 'release/r-51.0')
    develop_branch = get_config_value('DEVELOP_BRANCH', 'develop_branch', config, args, 'develop')
    bitbucket_base_url = get_config_value('BITBUCKET_BASE_URL', 'bitbucket_base_url', config, args,
                                         'https://bitbucket.insu.dev-1.us-east-1.guidewire.net/rest/api/1.0')
    commit_fetch_limit = get_config_value('COMMIT_FETCH_LIMIT', 'commit_fetch_limit', config, args, 100)
    cutoff_days = get_config_value('CUTOFF_DAYS', 'cutoff_days_before_code_freeze', config, args, 28)
    code_freeze_days = get_config_value('CODE_FREEZE_DAYS', 'code_freeze_days_before_release', config, args, 17)

    # SSL configuration
    ca_bundle = r"C:\certs\csaa_netskope_combined.pem"
    use_ca_bundle = True  # Set to False if CA bundle fails

    # Authentication
    bitbucket_auth = (bitbucket_email, bitbucket_token)
    bitbucket_headers = {"Accept": "application/json"}

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

    # Load Jira stories from CSV
    jira_csv_path = os.path.join(os.path.dirname(__file__), args.jira_csv)
    jira_story_data = load_jira_stories(jira_csv_path)

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
                    bitbucket_base_url, repo_name, branch, bitbucket_auth, bitbucket_headers, commit_fetch_limit
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
            "Issue Type": jira_story_data[story]["Issue_Type"],
            "Summary": jira_story_data[story]["Summary"],
            "App": jira_story_data[story]["App"],
            "Fix Version": jira_story_data[story]["Fix_Version"],
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