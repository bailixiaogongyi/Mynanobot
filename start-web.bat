@echo off
set "SCRIPT_DIR=%~dp0"
set "WEB_DIR=%SCRIPT_DIR%nanobot\web"

echo ========================================
echo   AiMate Web Startup Script
echo ========================================
echo.

echo [Step 1/3] Building frontend...
cd /d "%WEB_DIR%"
call npm run build
if errorlevel 1 (
    echo   [ERROR] Build failed
    pause
    exit /b 1
)
echo   Build completed
echo.

echo [Step 2/3] Starting backend...
echo   Backend: http://localhost:8080
start cmd /k "python -m nanobot gateway"
timeout /t 5 /nobreak >nul
echo.

echo [Step 3/3] Starting Vite dev server...
echo   Dev server: http://localhost:5173
start cmd /k "npm run dev"
echo.

echo ========================================
echo   Done!
echo   - Backend: http://localhost:8080
echo   - Dev server: http://localhost:5173
echo ========================================
pause
