@echo off
title World News Map — Starting...
echo.
echo  ============================================
echo   WORLD NEWS MAP — Trading Intelligence Hub
echo  ============================================
echo.

cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ first.
    pause
    exit /b 1
)

:: Install dependencies if needed
if not exist "backend\__installed__" (
    echo [SETUP] Installing Python dependencies...
    pip install -r backend\requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo. > backend\__installed__
    echo [SETUP] Dependencies installed.
)

echo.
echo [START] Launching API server on http://localhost:8888
echo [START] Dashboard at http://localhost:8888/dashboard
echo [START] API docs at http://localhost:8888/docs
echo.
echo  Bot endpoints:
echo    GET http://localhost:8888/api/signals
echo    GET http://localhost:8888/api/news/latest
echo    GET http://localhost:8888/api/news/breaking
echo    GET http://localhost:8888/api/market/crypto
echo    GET http://localhost:8888/api/market/forex
echo    GET http://localhost:8888/api/health
echo.
echo  Press Ctrl+C to stop.
echo  ============================================
echo.

:: Open dashboard in browser after 3 seconds
start "" /b cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:8888/dashboard"

:: Start the server
cd backend
python main.py
