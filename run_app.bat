@echo off
REM TeacherBot - One Command Startup Script
REM Usage: run_app.bat

REM Set title
title TeacherBot - Starting...

REM Check if node/npm is needed
echo.
echo ============================================
echo   TeacherBot - Initialization & Startup
echo ============================================
echo.

REM Activate virtual environment if exists
if exist .venv\Scripts\activate.bat (
    echo Activating Python environment...
    call .venv\Scripts\activate.bat
) else (
    echo Tip: Use a virtual environment for better isolation
    echo Run: python -m venv .venv
)

REM Install/update dependencies quietly
echo Setting up dependencies...
pip install -q -r requirements.txt >nul 2>&1

REM Run setup
python setup_env.py

REM Update title
title TeacherBot - Running on http://localhost:5000

REM Start Flask server
echo.
echo ============================================
echo   Server Starting... (Ctrl+C to stop)
echo ============================================
echo.
echo Access the app at: http://localhost:5000
echo.
echo To login with Gmail:
echo   1. Click "Email" tab in sidebar
echo   2. Click "Dang nhap Gmail" button
echo   3. Select your Gmail account
echo   4. Grant permissions
echo.
echo ============================================
echo.

python -m flask --app app run --debug

pause
