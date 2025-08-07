import os
import pandas as pd
import logging
from typing import Dict

logger = logging.getLogger(__name__)


def load_jira_excel(path: str) -> Dict[str, dict]:
    """Load Jira issues from an exported Excel file.

    The Excel file should contain at least the following columns:
    - Issue key
    - Summary
    - Issue type
    - Components
    - Fix version(s)
    """
    try:
        if path.lower().endswith(".csv"):
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)
    except Exception as exc:
        logger.error("Failed to read Jira Excel %s: %s", path, exc)
        raise

    # Normalize columns by making them lowercase and underscores
    df.columns = [str(col).strip().replace(" ", "_").lower() for col in df.columns]

    key_col = None
    for col in ["issue_key", "key"]:
        if col in df.columns:
            key_col = col
            break
    if not key_col:
        raise ValueError("Excel missing required column 'Issue key'")

    required = ["summary", "issue_type"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Excel missing required columns: {', '.join(missing)}")

    jira_base = os.getenv("JIRA_BASE_URL", "https://csaaig.atlassian.net/browse")
    stories = {}
    for _, row in df.iterrows():
        key = str(row[key_col]).strip().upper()
        stories[key] = {
            "Jira Story": key,
            "IssueType": row.get("issue_type", ""),
            "Summary": row.get("summary", ""),
            "App": row.get("components", ""),
            "FixVersion": row.get("fix_versions", ""),
            "Link": f"{jira_base.rstrip('/')}/{key}",
        }
    logger.info("Loaded %d Jira issues", len(stories))
    return stories
