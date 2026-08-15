# Start the local Arizona Deal Agent page, then open it in your default browser.
# Run from the repo folder:  powershell -ExecutionPolicy Bypass -File scripts\open-ui.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Create the venv first:  python -m venv .venv"
    exit 1
}

& .\.venv\Scripts\python.exe -m pip install -e ".[web]"
Write-Host ""
Write-Host "Starting local page at http://127.0.0.1:8000"
Write-Host "In Chrome or Opera: click the address bar (not Google search) and type that URL."
Write-Host "Leave this window open. Press Ctrl+C to stop."
Write-Host ""

Start-Process "http://127.0.0.1:8000"
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
