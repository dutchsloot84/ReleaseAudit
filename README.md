# Git vs Jira Excel Report

This tool compares Jira issues exported to Excel against Bitbucket commit history.

## Setup

1. Create a Python 3.9 environment.
2. Install dependencies (including `python-dotenv`):
   ```bash
   pip install -r requirements.txt
   ```
   The script will attempt this automatically if modules are missing.
3. Copy `.env.example` to `.env` and fill in your Bitbucket credentials.
4. Set `BITBUCKET_BASE_URL` in `.env` if your Bitbucket host differs from the
   default (`https://bitbucket.example.com/rest/api/1.0`).
5. Optionally set `JIRA_BASE_URL` for links to your Jira instance. The default
   is `https://csaaig.atlassian.net/browse`.
6. Optionally adjust `config.json` to list repositories and branches.
7. `commit_fetch_limit` in `config.json` controls how many commits are fetched per API page (default 100).

## Usage

Export issues from Jira as an Excel file (`.xlsx`) or CSV file containing columns such as *Issue key*, *Summary*, *Issue type*, *Components*, and *Fix version(s)*.

Run the tool (Windows):

```bat
run_gitxjira.bat --jira-excel path/to/jira.xlsx
```

macOS/Linux:

```bash
./run_gitxjira.command --jira-excel path/to/jira.xlsx
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
