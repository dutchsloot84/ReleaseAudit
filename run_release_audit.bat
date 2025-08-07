@echo off
setlocal
REM Optional venv activation
if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
)

REM Run with passthrough args
python src\main.py %*

REM Examples:
REM run_release_audit.bat
REM run_release_audit.bat --update-report gitxjira_report_20250805-1201.xlsx --merge-mode upsert
REM run_release_audit.bat --output my_report.xlsx
endlocal
