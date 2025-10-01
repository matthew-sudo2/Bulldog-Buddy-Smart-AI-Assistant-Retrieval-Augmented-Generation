@echo off
echo ============================================================
echo Starting Bulldog Buddy System
echo ============================================================
echo.

echo Starting API Bridge on port 8001...
start "API Bridge" powershell -NoExit -Command "cd '%~dp0'; .\.venv\Scripts\python.exe -m uvicorn api.bridge_server_enhanced:app --host 127.0.0.1 --port 8001"

timeout /t 5 /nobreak > nul

echo Starting Frontend on port 3000...
start "Frontend" powershell -NoExit -Command "cd '%~dp0frontend'; node server.js"

timeout /t 5 /nobreak > nul

echo.
echo ============================================================
echo All services started!
echo ============================================================
echo API Bridge:  http://127.0.0.1:8001/api/health
echo Frontend:    http://127.0.0.1:3000
echo.
echo Test Login:
echo Email:    test@example.com
echo Password: testpassword123
echo ============================================================
echo.
echo Press any key to check system status...
pause > nul

.\.venv\Scripts\python.exe check_system.py
