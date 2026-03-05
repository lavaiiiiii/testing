#!/usr/bin/env pwsh
# TeacherBot - One Command Startup Script
# Usage: .\run_app.ps1

# Colors
$title = "TeacherBot - Starting..."

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "   TeacherBot - Initialization & Startup" -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

# Activate virtual environment if exists  
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activating Python environment..." -ForegroundColor Yellow
    & ".venv\Scripts\Activate.ps1" 2>$null
} else {
    Write-Host "Tip: Use a virtual environment for better isolation" -ForegroundColor Gray
    Write-Host "Run: python -m venv .venv`n" -ForegroundColor Gray
}

# Install/update dependencies quietly
Write-Host "Setting up dependencies..." -ForegroundColor Yellow
python -m pip install -q -r requirements.txt 2>$null

# Run setup
Write-Host "`nInitializing application..." -ForegroundColor Yellow
python setup_env.py

# Start server
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "   Server Starting... (Ctrl+C to stop)" -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

Write-Host "Access the app at: " -NoNewline -ForegroundColor White
Write-Host "http://localhost:5000`n" -ForegroundColor Green

Write-Host "To login with Gmail:" -ForegroundColor Yellow
Write-Host "  1. Click 'Email' tab in sidebar" -ForegroundColor Gray
Write-Host "  2. Click 'Dang nhap Gmail' button" -ForegroundColor Gray
Write-Host "  3. Select your Gmail account" -ForegroundColor Gray
Write-Host "  4. Grant permissions" -ForegroundColor Gray

Write-Host "`n============================================`n" -ForegroundColor Cyan

python -m flask --app app run --debug
