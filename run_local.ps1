$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not (Test-Path ".env")) {
    Write-Host "[WARN] Chưa có file .env. Hãy copy .env.example thành .env và điền API keys." -ForegroundColor Yellow
}

if (-not (Test-Path "data/gmail_credentials.json")) {
    Write-Host "[WARN] Chưa có data/gmail_credentials.json. Gmail OAuth sẽ chưa hoạt động." -ForegroundColor Yellow
}

$pythonCandidates = @(
    "d:/job/.venv-2/Scripts/python.exe",
    ".venv/Scripts/python.exe",
    "venv/Scripts/python.exe"
)

$pythonExe = $null
foreach ($candidate in $pythonCandidates) {
    if (Test-Path $candidate) {
        $pythonExe = $candidate
        break
    }
}

if (-not $pythonExe) {
    Write-Host "[INFO] Không tìm thấy virtualenv, dùng python hệ thống." -ForegroundColor Yellow
    $pythonExe = "python"
}

Write-Host "[INFO] Python: $pythonExe" -ForegroundColor Cyan
Write-Host "[INFO] Cài dependencies nếu thiếu..." -ForegroundColor Cyan
& $pythonExe -m pip install -r requirements.txt | Out-Null

Write-Host "[INFO] Starting local server at http://localhost:5000" -ForegroundColor Green
& $pythonExe backend/app.py
