# Windows PowerShell script to launch the Streamlit Dashboard
# Usage: .\scripts\run_dashboard.ps1

$ErrorActionPreference = "Stop"

# 1. Determine Project Root Directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "   Big Data IT Recruitment - Dashboard Launcher   " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Project Root: $ProjectRoot"

# 2. Check Virtual Environment Python
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Virtual environment Python not found at: $PythonExe" -ForegroundColor Red
    Write-Host "Please create the virtual environment first: py -3.11 -m venv .venv" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Using Python: $PythonExe" -ForegroundColor Green

# 3. Check Streamlit Installation
& $PythonExe -c "import streamlit" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Streamlit is not installed in the virtual environment." -ForegroundColor Red
    Write-Host "Please install dependencies by running:" -ForegroundColor Yellow
    Write-Host "  & '$PythonExe' -m pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Streamlit is installed and ready." -ForegroundColor Green

# 4. Check App Entry Point
$AppPath = Join-Path $ProjectRoot "dashboard\app.py"
if (-not (Test-Path $AppPath)) {
    Write-Host "[ERROR] Dashboard entry point not found at: $AppPath" -ForegroundColor Red
    exit 1
}

# 5. Launch Streamlit
Write-Host "Launching Streamlit Dashboard..." -ForegroundColor Cyan
Write-Host "App URL: http://localhost:8501" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop the dashboard server." -ForegroundColor Gray
Write-Host "==================================================" -ForegroundColor Cyan

& $PythonExe -m streamlit run $AppPath
