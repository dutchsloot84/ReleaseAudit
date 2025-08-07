@echo off
setlocal EnableDelayedExpansion

rem Determine the directory of this script to allow relative execution
set SCRIPT_DIR=%~dp0
pushd %SCRIPT_DIR%

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
echo python %SCRIPT_DIR%main.py !MODE_ARG!
python "%SCRIPT_DIR%main.py" !MODE_ARG!

popd
pause
