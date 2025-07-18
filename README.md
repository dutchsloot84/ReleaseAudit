# Git vs Jira Excel Report

This tool compares Jira issues exported to Excel against Bitbucket commit history.

## Quick Start

1. Run `install_requirements.bat` (Windows) or `./install_requirements.bat` via Terminal on macOS to install the required packages using the included Python.
   The interpreter resides in `python/python-3.13.5-embed-amd64`.
2. Double‑click `run_release_audit.bat` (Windows) or run `./run_release_audit.command` on macOS/Linux.
3. Select your exported Jira file (`.csv` or `.xlsx`) and choose the run mode when prompted.
4. If credentials aren't set via environment variables, you'll be asked for your Bitbucket email and token.
5. The script outputs an Excel report in the `output` folder.

`config.json` lists repositories and branches to process. Adjust `commit_fetch_limit` if you need to fetch more commits per API page.

## Usage

Export issues from Jira as an Excel file (`.xlsx`) or CSV file containing columns such as *Issue key*, *Summary*, *Issue type*, *Components*, and *Fix version(s)*.

Run the tool manually:

```bat
python main.py --jira-excel path/to/jira.xlsx
```

For a guided experience that lets you pick the Jira file and run mode:

Windows:
```bat
run_release_audit.bat
```

macOS/Linux:
```bash
./run_release_audit.command
```

Or directly with Python:

```bash
python main.py --jira-excel path/to/jira.xlsx
```
Only process the release branch:
```bash
python main.py --jira-excel path/to/jira.xlsx --release-only
```
Only process the develop branch:
```bash
python main.py --jira-excel path/to/jira.xlsx --develop-only
```
CSV files can be provided in the same way:
```bash
python main.py --jira-excel path/to/jira.csv
```
If your file name contains spaces, wrap it in quotes:
```bash
python main.py --jira-excel "Release Audit.csv"
```
Ensure you run `main.py` as the script (the `.csv` file should be passed with `--jira-excel`).

Additional options:

- `--develop-branch` specify a different develop branch.
- `--release-branch` specify a different release branch.
- `--develop-only` process only the develop branch.
- `--release-only` process only the release branch.
- `--config` path to configuration JSON.
- adjust `commit_fetch_limit` in `config.json` to fetch more commits per page.

The script outputs an Excel report `gitxjira_report_<timestamp>.xlsx` with Jira stories, commit details, and any stories missing from Git.
