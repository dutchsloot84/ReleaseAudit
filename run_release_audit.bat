@echo off
setlocal EnableDelayedExpansion

rem Determine the directory of this script to allow relative execution
set SCRIPT_DIR=%~dp0
pushd %SCRIPT_DIR%

set IDX=0
for %%f in (*.csv *.xlsx) do (
    set /a IDX+=1
    set "FILE!IDX!=%%~f"
    echo   !IDX!. %%~f
)

if %IDX%==0 (
    echo No .csv or .xlsx files found in %CD%.
)

set /p CHOICE=Enter the number of the file to use, or press Enter to manually input a file path: 
if "%CHOICE%"=="" (
    set /p FILEPATH=Enter the path to the Jira file: 
) else (
    set FILEPATH=!FILE%CHOICE%!
    if "!FILEPATH!"=="" (
        echo Invalid choice. Please provide a file path manually.
        set /p FILEPATH=Enter the path to the Jira file: 
    )
)

set MODE_ARG=


echo Choose run mode:
echo   1. Full run (release + develop)
echo   2. Develop only
echo   3. Release only
set /p MODE=Enter 1, 2, or 3: 
if "%MODE%"=="2" (
    set MODE_ARG=--develop-only
) else if "%MODE%"=="3" (
    set MODE_ARG=--release-only
)

echo Running:
echo python %SCRIPT_DIR%main.py --jira-excel "!FILEPATH!" !MODE_ARG!
python "%SCRIPT_DIR%main.py" --jira-excel "!FILEPATH!" !MODE_ARG!

popd
pause
