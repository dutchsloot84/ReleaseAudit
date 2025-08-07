# src/commit_processor.py
"""Utilities for parsing commit messages and extracting Jira story data."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

# Precompiled regex patterns
STORY_PATTERN = re.compile(r"[A-Z]+-\d+", re.IGNORECASE)
VALIDATION_PATTERN = re.compile(r"^[A-Z]+-\d+$")
CONCAT_PATTERN = re.compile(r"([A-Z]+-\d+)([_-]\w+)+", re.IGNORECASE)

def clean_commit_message(message: str) -> str:
    """Normalize commit messages by stripping whitespace and odd characters."""
    message = re.sub(r"[\r\n\t]+", " ", message)
    message = re.sub(r"\s+", " ", message)
    message = message.replace("'", "").replace("\\u0027", "")
    message = re.sub(r"[^a-zA-Z0-9\s:/_.-]", "", message)
    return message.strip()

def preprocess_commit_message(message: str) -> str:
    """Break apart concatenated story numbers in a commit message."""
    preprocessed_message = message
    for match in CONCAT_PATTERN.finditer(message):
        full_match = match.group(0)
        prefix = match.group(1)
        preprocessed_message = preprocessed_message.replace(full_match, prefix)
    logger.debug("Preprocessed '%s' to '%s'", message, preprocessed_message)
    return preprocessed_message

def extract_stories(
    commit: dict,
    fix_version: str,
    jira_story_data: Dict[str, dict],
    app_name: str,
    commit_hash: str,
    branch: str,
    cutoff_date_obj: datetime,
    code_freeze_date: datetime,
    develop_branch: str,
    git_story_numbers: Dict[str, str],
    commit_hashes: Dict[str, str],
    bitbucket_base_url: str,
    repo_name: str,
    exclude_patterns: Optional[Iterable[str]] = None,
) -> List[dict]:
    """Extract Jira story references from a commit.

    Returns a list of dictionaries representing commit rows enriched with
    metadata for later reporting.
    """
    if exclude_patterns is None:
        exclude_patterns = []
    exclude_regex = [re.compile(pattern, re.IGNORECASE) for pattern in exclude_patterns]

    commit_date = datetime.fromtimestamp(commit["authorTimestamp"] / 1000)
    if commit_date < cutoff_date_obj or (branch == develop_branch and commit_date > code_freeze_date):
        logger.debug(f"Skipping commit {commit_hash} - outside date range ({commit_date})")
        return []

    raw_message = commit["message"]
    logger.debug(f"Raw commit message for {commit_hash}: '{raw_message}'")
    cleaned_message = clean_commit_message(raw_message)
    preprocessed_message = preprocess_commit_message(cleaned_message)

    story_matches = STORY_PATTERN.finditer(preprocessed_message)
    filtered_commits = []
    for match in story_matches:
        story_number = match.group().strip().upper()
        logger.debug(f"Matched story number: {story_number} (at index {match.start()})")
        
        # Check against exclude patterns
        if any(pattern.match(story_number) for pattern in exclude_regex):
            logger.debug(f"Excluding {story_number} due to matching exclude pattern")
            continue

        if VALIDATION_PATTERN.match(story_number):
            if story_number in jira_story_data and jira_story_data[story_number]["FixVersion"] != fix_version:
                logger.debug(f"Skipping {story_number} - fixVersion mismatch")
                continue
            git_story_numbers[story_number] = app_name
            commit_hashes[story_number] = commit_hash
            issue_type = jira_story_data.get(story_number, {}).get("IssueType", "Unknown")
            fix_version_field = jira_story_data.get(story_number, {}).get("FixVersion", "Unknown")
            app = jira_story_data.get(story_number, {}).get("App", app_name)
            project, repo = repo_name.split("/", 1)
            commit_url = (
                f"{bitbucket_base_url}/projects/{project}/repos/{repo}/commits/{commit_hash}"
            )
            filtered_commits.append(
                {
                    "Commit Hash": commit_hash,
                    "Commit URL": commit_url,
                    "Message": cleaned_message,
                    "Issue Type": issue_type,
                    "App": app,
                    "FixVersion": fix_version_field,
                    "Commit Source": branch,
                }
            )
        else:
            logger.debug(f"Invalid story number format: {story_number}")

    if not filtered_commits:
        logger.debug(f"No valid stories extracted from commit {commit_hash}")
    return filtered_commits

# 🔍 NEW FUNCTION: Extract all matched and unmatched commits
def extract_story_mappings(commits: Iterable[dict], **kwargs) -> tuple[List[dict], List[dict]]:
    """Run :func:`extract_stories` across commits returning matched and orphan lists."""
    all_filtered_commits: List[dict] = []
    orphan_commits: List[dict] = []

    for commit in commits:
        commit_hash = commit["id"]
        extracted = extract_stories(commit=commit, commit_hash=commit_hash, **kwargs)
        if extracted:
            all_filtered_commits.extend(extracted)
        else:
            orphan_commits.append(commit)

    return all_filtered_commits, orphan_commits
