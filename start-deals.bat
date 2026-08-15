@echo off
setlocal
cd /d "%~dp0"

echo DEALS DEALS DEALS
echo.

if not exist pyproject.toml (
    echo Wrong folder.
    echo This window is in:
    echo   %CD%
    echo.
    echo start-deals.bat must stay inside the unzipped Arizona-Deal-Agent folder
    echo ^(the folder that contains pyproject.toml^).
    echo.
    echo If you have not downloaded the project yet, open Command Prompt and paste:
    echo   cd /d C:\Users\%USERNAME%
    echo   curl.exe -L -o Arizona-Deal-Agent.zip https://github.com/F03F03s44s/Arizona-Deal-Agent/archive/refs/heads/main.zip
    echo   tar -xf Arizona-Deal-Agent.zip
    echo   cd Arizona-Deal-Agent-main
    echo   start-deals.bat
    echo.
    pause
    exit /b 1
)

echo Project folder: %CD%
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install Python 3 from https://www.python.org/downloads/
    echo and check "Add python.exe to PATH".
    pause
    exit /b 1
)

if not exist .venv\Scripts\python.exe (
    echo Creating .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo Could not create .venv
        pause
        exit /b 1
    )
)

echo Installing DEALS DEALS DEALS ...
.\.venv\Scripts\python.exe -m pip install -e ".[web]"
if errorlevel 1 (
    echo Install failed. Stay in this folder and try again.
    pause
    exit /b 1
)

echo.
echo Starting http://127.0.0.1:8000
echo Leave this window open.
echo In Chrome or Opera: click the ADDRESS BAR ^(not Google search^)
echo and type:  http://127.0.0.1:8000
echo Press Ctrl+C to stop.
echo.

start "" "http://127.0.0.1:8000"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
