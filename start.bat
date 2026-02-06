@echo off
echo ======================================
echo Multi-Agent PSUR System - STARTUP
echo ======================================
echo.

REM Check if we're in the right directory
if not exist "backend" (
    echo Error: Please run from project root directory
    pause
    exit /b 1
)

echo Starting both backend and frontend...
echo.
echo Backend will run on: http://127.0.0.1:8000
echo Frontend will run on: http://localhost:3000
echo.
echo Press Ctrl+C in each window to stop
echo ======================================
echo.

REM Initialize database only if it does not exist
if not exist "psur_system.db" (
    echo Initializing database for the first time...
    python quickstart.py
    echo.
) else (
    echo Database already exists, skipping init.
    echo.
)

REM Clear stale bytecache to ensure all routes load
for /d /r backend %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
echo Cleared Python bytecache.
echo.

REM Start backend in new window
start "PSUR Backend" cmd /k "cd /d %CD% && uvicorn backend.main:app --reload --port 8000 --reload-dir backend"

REM Wait 3 seconds for backend to start
timeout /t 3 /nobreak > nul

REM Start frontend in new window  
start "PSUR Frontend" cmd /k "cd /d %CD%\frontend && npm run dev"

REM Wait 2 seconds
timeout /t 2 /nobreak > nul

echo.
echo System starting in separate windows!
echo.
echo When both servers are ready, open:
echo    http://localhost:3000
echo.
pause
