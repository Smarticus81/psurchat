@echo off
echo ======================================
echo 🚀 Multi-Agent PSUR System - STARTUP
echo ======================================
echo.

REM Check if we're in the right directory
if not exist "backend" (
    echo ❌ Error: Please run from project root directory
    pause
    exit /b 1
)

echo 📋 Starting both backend and frontend...
echo.
echo Backend will run on: http://127.0.0.1:8000
echo Frontend will run on: http://localhost:3000
echo.
echo Press Ctrl+C in each window to stop
echo ======================================
echo.

REM Initialize database first
echo Initializing database...
python reset_db.py
echo.

REM Start backend in new window
start "PSUR Backend" cmd /k "cd /d %CD% && uvicorn backend.main:app --reload --port 8000"

REM Wait 3 seconds for backend to start
timeout /t 3 /nobreak > nul

REM Start frontend in new window  
start "PSUR Frontend" cmd /k "cd /d %CD%\frontend && npm run dev"

REM Wait 2 seconds
timeout /t 2 /nobreak > nul

echo.
echo ✅ System starting in separate windows!
echo.
echo When both servers are ready, open:
echo    http://localhost:3000
echo.
pause
