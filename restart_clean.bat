@echo off
echo ======================================
echo 🔄 CLEAN RESTART - PSUR System
echo ======================================
echo.
echo This will:
echo 1. Stop all running processes
echo 2. Delete old database
echo 3. Recreate database with new schema  
echo 4. Restart backend and frontend
echo.
pause

REM Kill any existing processes
echo Stopping existing processes...
taskkill /F /FI "WINDOWTITLE eq PSUR Backend*" 2>nul
taskkill /F /FI "WINDOWTITLE eq PSUR Frontend*" 2>nul
timeout /t 2 /nobreak > nul

REM Delete old database
echo Deleting old database...
if exist "psur_system.db" (
    del /F /Q "psur_system.db"
    echo ✅ Old database deleted
) else (
    echo ℹ️  No database found
)
echo.

REM Recreate database
echo Creating fresh database...
python reset_db.py
echo.

REM Start both servers
echo Starting backend and frontend...
start "PSUR Backend" cmd /k "cd /d %CD% && uvicorn backend.main:app --reload --port 8000"
timeout /t 3 /nobreak > nul
start "PSUR Frontend" cmd /k "cd /d %CD%\frontend && npm run dev"

echo.
echo ✅ Clean restart complete!
echo.
echo Backend: http://127.0.0.1:8000
echo Frontend: http://localhost:3000
echo.
pause
