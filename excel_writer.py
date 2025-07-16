# src/excel_writer.py
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def write_excel(all_commits, missing_stories_data, output_file):
    """
    Write commit data and missing stories to an Excel file.
    
    Args:
        all_commits (dict): Dictionary of app_name to list of commits.
        missing_stories_data (list): List of missing stories data.
        output_file (str): Path to the output Excel file.
    """
    # Export commits to Excel
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for app_name, commits in all_commits.items():
            logger.info(f"Exporting {app_name} with {len(commits)} commits")
            df = pd.DataFrame(commits)
            df.to_excel(writer, sheet_name=app_name, index=False)

    # Export Missing Jira Stories
    if missing_stories_data:
        df_missing = pd.DataFrame(missing_stories_data)
        with pd.ExcelWriter(output_file, engine='openpyxl', mode='a') as writer:
            df_missing.to_excel(writer, sheet_name="Missing Jira Stories", index=False)
    else:
        logger.info(
            "No missing Jira stories found or no commits fetched to compare."
        )
