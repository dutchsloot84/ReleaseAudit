@echo off
setlocal

rem Determine script dir
set SCRIPT_DIR=%~dp0
pushd %SCRIPT_DIR%

set PYTHON_DIR=%SCRIPT_DIR%python\python-3.13.5-embed-amd64
set PYTHON_PATH=%PYTHON_DIR%\python.exe
set GET_PIP=%PYTHON_DIR%\get-pip.py

for %%f in ("%PYTHON_DIR%\python*._pth") do set PTH_FILE=%%f
if exist "%PTH_FILE%" (
    rem Ensure script directory is on the path
    findstr /x "." "%PTH_FILE%" >nul 2>&1
    if errorlevel 1 (
        echo .>>"%PTH_FILE%"
    )
    rem Enable site so pip and PYTHONPATH work
    findstr /b /c:"import site" "%PTH_FILE%" >nul 2>&1
    if errorlevel 1 (
        echo import site>>"%PTH_FILE%"
    )
)

"%PYTHON_PATH%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo Installing pip...
    "%PYTHON_PATH%" "%GET_PIP%"
)

"%PYTHON_PATH%" -m pip install --upgrade pip
"%PYTHON_PATH%" -m pip install -r requirements.txt

popd
