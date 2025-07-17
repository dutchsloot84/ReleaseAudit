import argparse
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from tqdm import tqdm

from config_loader import load_config
from bitbucket_api import fetch_commits
from excel_loader import load_jira_excel
from commit_processor import extract_stories
from excel_writer import write_excel

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    # If the user accidentally runs a CSV/XLSX file as the Python script
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith((".csv", ".xlsx")):
        print(
            "It looks like you tried to run a data file as the script. "
            "Run:\n  python main.py --jira-excel \"%s\"" % sys.argv[1]
        )
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Compare Jira issues against Bitbucket commits"
    )
    parser.add_argument(
        "--jira-excel", required=True, help="Path to exported Jira Excel or CSV file"
    )
    parser.add_argument("--config", default="config.json", help="Path to JSON config file")
    parser.add_argument("--develop-branch", help="Develop branch name override")
    parser.add_argument("--release-branch", help="Release branch name override")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--dry-run", action="store_true", help="Validate setup without network calls")

    branch_group = parser.add_mutually_exclusive_group()
    branch_group.add_argument(
        "--develop-only",
        action="store_true",
        help="Process only the develop branch",
    )
    branch_group.add_argument(
        "--release-only",
        action="store_true",
        help="Process only the release branch",
    )
    return parser.parse_args()


def build_branches(args, config: Dict[str, str]) -> List[str]:
    develop = args.develop_branch or config.get("develop_branch", "develop")
    release = args.release_branch or config.get("release_branch", "release")
    if args.develop_only:
        return [develop]
    if args.release_only:
        return [release]
    return [develop, release]


def process_repo(
    repo_name: str,
    app_name: str,
    branches: List[str],
    cfg: Dict[str, str],
    jira_story_data: Dict[str, dict],
    cutoff: datetime,
    freeze: datetime,
    auth,
    headers,
    limit: int,
    develop_branch: str,
    git_story_numbers: Dict[str, str],
    commit_hashes: Dict[str, str],
) -> List[dict]:
    results = []
    for branch in branches:
        logger.info("Processing repo %s on branch %s", repo_name, branch)
        commits = fetch_commits(
            cfg["bitbucket_base_url"],
            repo_name,
            branch,
            auth,
            headers,
            limit,
            start_date=cutoff,
            end_date=freeze,
        )
        for commit in commits:
            extracted = extract_stories(
                commit=commit,
                fix_version=cfg.get("fix_version", ""),
                jira_story_data=jira_story_data,
                app_name=app_name,
                commit_hash=commit["id"],
                branch=branch,
                cutoff_date_obj=cutoff,
                code_freeze_date=freeze,
                develop_branch=develop_branch,
                git_story_numbers=git_story_numbers,
                commit_hashes=commit_hashes,
                exclude_patterns=[],
            )
            results.extend(extracted)
    return results


def main() -> None:
    args = parse_args()

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    log_file = log_dir / f"{timestamp}-gitxjira.log"

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )

    logger.info("Loading configuration...")
    config_path = Path(args.config)
    config = load_config(str(config_path))

    jira_path = Path(args.jira_excel)
    if not jira_path.exists():
        logger.error("Jira Excel file %s not found", jira_path)
        sys.exit(1)

    bitbucket_email = os.getenv("BITBUCKET_EMAIL")
    bitbucket_token = os.getenv("BITBUCKET_TOKEN")
    if not bitbucket_email or not bitbucket_token:
        logger.error("BITBUCKET_EMAIL and BITBUCKET_TOKEN must be set in .env")
        sys.exit(1)

    if args.dry_run:
        logger.info("Dry run successful. Configuration and environment look good")
        logger.info("Log file written to %s", log_file)
        return

    repos = config.get("repos", {})
    develop_branch = args.develop_branch or config.get("develop_branch", "develop")
    release_branch = args.release_branch or config.get("release_branch", "release")
    branches = build_branches(args, config)
    fix_version = config.get("fix_version", "")
    base_url = os.getenv(
        "BITBUCKET_BASE_URL",
        config.get("bitbucket_base_url", "https://bitbucket.example.com/rest/api/1.0"),
    )
    commit_limit = int(config.get("commit_fetch_limit", 25))
    cutoff_days = int(config.get("cutoff_days_before_code_freeze", 28))
    freeze_days = int(config.get("code_freeze_days_before_release", 17))

    release_date = datetime.strptime(fix_version.replace("Mobilitas ", ""), "%Y.%m.%d") if fix_version else datetime.now()
    code_freeze_date = release_date - timedelta(days=freeze_days)
    cutoff_date = code_freeze_date - timedelta(days=cutoff_days)

    logger.info("Loading Jira stories...")
    jira_story_data = load_jira_excel(str(jira_path))

    auth = (bitbucket_email, bitbucket_token)
    headers = {"Accept": "application/json"}

    all_commits: Dict[str, List[dict]] = {}
    git_story_numbers: Dict[str, str] = {}
    commit_hashes: Dict[str, str] = {}
    logger.info("Processing repositories...")
    with ThreadPoolExecutor(max_workers=4) as executor, tqdm(total=len(repos), desc="Repos") as progress:
        futures = {}
        for repo_name, app_name in repos.items():
            futures[executor.submit(
                process_repo,
                repo_name,
                app_name,
                branches,
                {
                    "bitbucket_base_url": base_url,
                    "fix_version": fix_version,
                },
                jira_story_data,
                cutoff_date,
                code_freeze_date,
                auth,
                headers,
                commit_limit,
                develop_branch,
                git_story_numbers,
                commit_hashes,
            )] = (repo_name, app_name)

        for future in as_completed(futures):
            repo_name, app_name = futures[future]
            progress.set_description(f"{repo_name}")
            progress.update(1)
            try:
                commits = future.result()
                if commits:
                    all_commits.setdefault(app_name, []).extend(commits)
            except Exception:
                logger.exception("Failed processing %s", repo_name)

    missing = [story for story in jira_story_data if story not in git_story_numbers]
    missing_data = [jira_story_data[s] | {"Missing From": "Git", "Notes": ""} for s in missing]

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    output_file = output_dir / f"gitxjira_report_{timestamp}.xlsx"
    write_excel(all_commits, missing_data, str(output_file))
    logger.info("Report written to %s", output_file)
    logger.info("Log file written to %s", log_file)


if __name__ == "__main__":
    main()
