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
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        if all_commits:
            for app_name, commits in all_commits.items():
                logger.info("Exporting %s with %d commits", app_name, len(commits))
                pd.DataFrame(commits).to_excel(writer, sheet_name=app_name, index=False)
        else:
            pd.DataFrame({"Info": ["No commit data fetched"]}).to_excel(
                writer, sheet_name="Commits", index=False
            )

        if missing_stories_data:
            df = pd.DataFrame(missing_stories_data)
            if "Status" in df.columns and "App" in df.columns:
                cols = df.columns.tolist()
                cols.remove("Status")
                app_index = cols.index("App")
                cols.insert(app_index + 1, "Status")
                df = df[cols]
            df.to_excel(writer, sheet_name="Missing Jira Stories", index=False)
        else:
            logger.info("No missing Jira stories found or no commits fetched to compare.")
