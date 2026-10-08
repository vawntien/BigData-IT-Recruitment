# Environment verification script for Dashboard development
# Usage: .\scripts\check_dashboard_env.ps1

$ErrorActionPreference = "Continue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " Dashboard Environment Verification Health Check  " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$AllPassed = $true

# 1. Check Python
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path $PythonExe) {
    $PyVersion = & $PythonExe --version 2>&1
    Write-Host "[PASS] Python virtual environment: $PyVersion" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Python virtual environment not found at: $PythonExe" -ForegroundColor Red
    $AllPassed = $false
}

# 2. Check Streamlit
if (Test-Path $PythonExe) {
    $StVersion = & $PythonExe -m streamlit --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[PASS] Streamlit package: $StVersion" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Streamlit not installed in .venv" -ForegroundColor Red
        $AllPassed = $false
    }
}

# 3. Check Dashboard Project Files
$RequiredFiles = @(
    "dashboard\app.py",
    "dashboard\pages\1_Overview.py",
    "dashboard\pages\2_Skills.py",
    "dashboard\pages\3_Salary_Quality.py",
    "dashboard\components\data_loader.py",
    "dashboard\components\contract_validator.py",
    "dashboard\components\filters.py",
    "dashboard\components\ui_helpers.py"
)

foreach ($RelFile in $RequiredFiles) {
    $FullPath = Join-Path $ProjectRoot $RelFile
    if (Test-Path $FullPath) {
        Write-Host "[PASS] File found: $RelFile" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Missing file: $RelFile" -ForegroundColor Red
        $AllPassed = $false
    }
}

# 4. Check Sample Data Files
$SampleFiles = @(
    "dashboard\sample_data\overview_sample.csv",
    "dashboard\sample_data\skills_sample.csv",
    "dashboard\sample_data\salary_quality_sample.csv"
)

foreach ($RelFile in $SampleFiles) {
    $FullPath = Join-Path $ProjectRoot $RelFile
    if (Test-Path $FullPath) {
        Write-Host "[PASS] Sample data: $RelFile" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Missing sample data: $RelFile" -ForegroundColor Red
        $AllPassed = $false
    }
}

# 5. Check Analytics Directory
$AnalyticsDir = Join-Path $ProjectRoot "data\analytics"
if (Test-Path $AnalyticsDir) {
    $ProdFiles = Get-ChildItem -Path $AnalyticsDir -File | Where-Object { $_.Name -ne ".gitkeep" }
    if ($ProdFiles.Count -gt 0) {
        Write-Host "[INFO] Production analytics data present ($($ProdFiles.Count) files)" -ForegroundColor Cyan
    } else {
        Write-Host "[INFO] Analytics directory exists (currently empty, waiting for A06-A08)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[FAIL] Missing data/analytics directory" -ForegroundColor Red
    $AllPassed = $false
}

Write-Host "==================================================" -ForegroundColor Cyan
if ($AllPassed) {
    Write-Host "OVERALL STATUS: ALL CHECKS PASSED - READY FOR DEVELOPMENT!" -ForegroundColor Green
} else {
    Write-Host "OVERALL STATUS: SOME CHECKS FAILED - PLEASE REVIEW ABOVE." -ForegroundColor Red
}
Write-Host "==================================================" -ForegroundColor Cyan
