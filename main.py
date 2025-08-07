import argparse
import logging
import os
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

from tqdm import tqdm

from config_loader import load_config
from bitbucket_api import fetch_commits
from jira_client import load_jira_issues
from commit_processor import extract_stories
from excel_writer import write_excel

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Jira issues against Bitbucket commits"
    )
    parser.add_argument("--config", default="config.json", help="Path to JSON config file")
    parser.add_argument("--develop-branch", help="Develop branch name override")
    parser.add_argument("--release-branch", help="Release branch name override")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--dry-run", action="store_true", help="Validate setup without network calls")
    parser.add_argument("--open", action="store_true", help="Open the Excel report when done")

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


def ensure_directories() -> Tuple[Path, Path]:
    """Ensure log and output directories exist."""
    log_dir = Path("logs")
    output_dir = Path("output")
    log_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    return log_dir, output_dir




def ensure_credentials(env_path: Path) -> Tuple[str, str]:
    """Ensure Bitbucket credentials are available, prompting if needed."""
    email = os.getenv("BITBUCKET_EMAIL")
    token = os.getenv("BITBUCKET_TOKEN")
    if email and token:
        return email, token

    print("Bitbucket credentials not found in .env.\n")
    email = input("Bitbucket Email: ").strip()
    token = input("Bitbucket Token: ").strip()
    # Append to .env
    with env_path.open("a", encoding="utf-8") as f:
        if email:
            f.write(f"BITBUCKET_EMAIL={email}\n")
        if token:
            f.write(f"BITBUCKET_TOKEN={token}\n")
    os.environ["BITBUCKET_EMAIL"] = email
    os.environ["BITBUCKET_TOKEN"] = token
    return email, token


def open_file(path: Path) -> None:
    """Open a file using the default program for the OS."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])
    except Exception as exc:
        logger.warning("Could not open %s: %s", path, exc)


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
        for commit in tqdm(commits, desc=f"{app_name}-{branch}", leave=False):
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

    # Ensure required folders exist
    log_dir, output_dir = ensure_directories()
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

    env_path = config_path.resolve().parent / ".env"
    bitbucket_email, bitbucket_token = ensure_credentials(env_path)

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
    commit_limit = int(config.get("commit_fetch_limit", 100))
    cutoff_days = int(config.get("cutoff_days_before_code_freeze", 28))
    freeze_days = int(config.get("code_freeze_days_before_release", 17))

    release_date = datetime.strptime(fix_version.replace("Mobilitas ", ""), "%Y.%m.%d") if fix_version else datetime.now()
    code_freeze_date = release_date - timedelta(days=freeze_days)
    cutoff_date = code_freeze_date - timedelta(days=cutoff_days)

    logger.info("Loading Jira stories via API...")
    jira_story_data = load_jira_issues(fix_version)

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

    missing = []
    for story in tqdm(jira_story_data, desc="Jira compare", leave=False):
        if story not in git_story_numbers:
            missing.append(story)
    missing_data = [jira_story_data[s] | {"Missing From": "Git", "Notes": ""} for s in missing]

    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    output_file = output_dir / f"gitxjira_report_{timestamp}.xlsx"
    with tqdm(total=1, desc="Writing Excel", leave=False):
        write_excel(all_commits, missing_data, str(output_file))
        tqdm.write("Excel report generated")
    logger.info("Report written to %s", output_file)
    logger.info("Log file written to %s", log_file)

    print("\nReport saved to", output_file)
    print("Log file:", log_file)

    if args.open:
        open_file(output_file)


if __name__ == "__main__":
    main()
