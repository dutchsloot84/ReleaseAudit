@echo off
setlocal

rem Determine script dir
set SCRIPT_DIR=%~dp0
pushd %SCRIPT_DIR%

.\python\python.exe -m pip install --upgrade pip
.\python\python.exe -m pip install -r requirements.txt

popd
