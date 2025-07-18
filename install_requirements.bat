@echo off
setlocal

rem Determine script dir
set SCRIPT_DIR=%~dp0
pushd %SCRIPT_DIR%

set PYTHON_PATH=%SCRIPT_DIR%python\python-3.13.5-embed-amd64\python.exe

"%PYTHON_PATH%" -m pip install --upgrade pip
"%PYTHON_PATH%" -m pip install -r requirements.txt

popd
