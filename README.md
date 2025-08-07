# Git vs Jira Release Audit

This tool compares Jira issues retrieved from the Jira Cloud REST API against Bitbucket commit history.

## Getting Started

1. **Install Python** – The scripts require Python 3.9 or newer. If you do not
   already have Python:
   - Windows/macOS: download it from [python.org](https://www.python.org/downloads/)
     and ensure the `python` command is added to your `PATH` during install.
   - macOS via Homebrew: `brew install python@3.9`
   - Linux: install `python3` using your distribution's package manager.
2. **Install certificates** – If API requests to Bitbucket fail due to SSL
   errors, you may need to install the certificate bundle that ships with
   Python. Look for `Install Certificates.command` in your Python installation
   directory and run it. For corporate Bitbucket instances using custom or
   self-signed certificates, set the `REQUESTS_CA_BUNDLE` environment variable
   to the path of your `.pem` file.
3. **Clone this repository** – `git clone <repo-url>` or download the source as
   a ZIP archive and extract it.

## Setup

1. Create a Python 3.9 virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
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

### ✅ Jira OAuth Setup

1. Visit <https://developer.atlassian.com/console/myapps>
2. Register a **3LO OAuth App** (Authorization Code Grant)
3. Set Redirect URL: `http://localhost:8080/callback`
4. Save the Client ID and Client Secret

### 🚀 One-Time Token Setup

1. Open this browser URL (replace `YOUR_CLIENT_ID`):

   <https://auth.atlassian.com/authorize?audience=api.atlassian.com&client_id=YOUR_CLIENT_ID&scope=read:jira-user%20read:jira-work%20write:jira-work%20offline_access&redirect_uri=http://localhost:8080/callback&state=xyz123&response_type=code&prompt=consent>

2. Approve the app and copy the `code` from the URL
3. Generate `jira_token.json` by running:

   ```bash
   python write_jira_token.py YOUR_CLIENT_ID YOUR_CLIENT_SECRET YOUR_CODE
   ```

   Use `--redirect-uri` if you specified a custom redirect during the OAuth
   setup.

4. The script writes `jira_token.json` locally next to your source files.

> 🛡️ **Important**: Do not commit `jira_token.json`. It contains sensitive credentials. It is ignored by `.gitignore`.

### 🖥️ GUI Token Setup

Instead of manually copying the authorization code, you can run a small GUI helper located in `token_generator/`:

```bash
python token_generator/gui_token_setup.py
```

Follow the prompts to enter your *Client ID* and *Client Secret*. The tool launches your browser for approval and saves `jira_token.json` automatically. To build a standalone executable use:

```bash
pyinstaller --onefile token_generator/gui_token_setup.py
```


#### 🔁 If Token Expires

If `refresh_token` is older than 30 days or fails:
- Repeat the above process to get a new `code` and generate a new `jira_token.json`

## Usage

Jira stories are fetched automatically using the fix version defined in `config.json`.

Run the tool (Windows):

```bat
run_release_audit.bat
```

Or directly with Python:

```bash
python main.py
```

Only process the release branch:
```bash
python main.py --release-only
```
Only process the develop branch:
```bash
python main.py --develop-only
```

Additional options:

- `--develop-branch` specify a different develop branch.
- `--release-branch` specify a different release branch.
- `--develop-only` process only the develop branch.
- `--release-only` process only the release branch.
- `--config` path to configuration JSON.
- adjust `commit_fetch_limit` in `config.json` to fetch more commits per page.

The script outputs an Excel report `gitxjira_report_<timestamp>.xlsx` with Jira stories, commit details, and any stories missing from Git. In the "Missing Jira Stories" worksheet the **Status** column appears immediately after **App** so you can quickly see the state of each issue.

## Troubleshooting

* **401/403 errors from Jira** – The access token may have expired. Regenerate `jira_token.json` using the **One-Time Token Setup** steps.
* **SSL certificate failures** – Ensure you installed the certificate bundle or set `REQUESTS_CA_BUNDLE` to your internal certificate authority file.
* **No stories returned** – Verify the `fix_version` in `config.json` matches the release in Jira and that your account has permission to read those issues.
