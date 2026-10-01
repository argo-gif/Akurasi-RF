@echo off
echo ========================================================
echo   Demand Planning & Forecast Accuracy Server Launcher
echo ========================================================
echo.
echo Starting Backend API Server (http://localhost:8050)...
start "Backend API Server" cmd /k "python backend/main.py"

echo Starting Frontend Web Server (http://localhost:3000)...
start "Frontend Web Server" cmd /k "python -m http.server 3000 --directory frontend"

echo.
echo Beide server telah dijalankan!
echo - Frontend Dashboard: http://localhost:3000
echo - Backend REST API:   http://localhost:8050
echo.
pause
