@echo off
chcp 65001 >nul
REM Project Startup Script (Optimized for Portable Python)
setlocal enabledelayedexpansion

REM ===================== CONFIG =====================
REM 定义便携式Python环境路径
SET PORTABLE_PYTHON=%~dp0backend\python313\python.exe
REM ==================================================

REM Set portable Node.js path
SET NODE_DIR=%~dp0node_env
SET PATH=%NODE_DIR%;%PATH%

REM Check Node.js
IF NOT EXIST "%NODE_DIR%\node.exe" (
    echo Error: Portable Node.js not found at %NODE_DIR%\node.exe
    echo Please extract Node.js binaries into the "node_env" folder.
    pause
    exit /b 1
)
echo ✅ Portable Node.js loaded

REM Use only portable Python environment
SET "PYTHON_EXE="
IF EXIST "%PORTABLE_PYTHON%" (
    SET "PYTHON_EXE=%PORTABLE_PYTHON%"
    echo ✅ Portable Python environment detected
) ELSE (
    echo ERROR: No Python environment found!
    echo Please ensure portable Python exists at:
    echo %PORTABLE_PYTHON%
    pause
    exit /b 1
)

echo Using Python: !PYTHON_EXE!

REM Install frontend dependencies
cd /d %~dp0frontend
IF NOT EXIST "node_modules" (
    echo Installing frontend dependencies...
    npm install
)

REM Start Backend Server (using the correct Python executable)
start "Backend Server" cmd /k "cd /d "%~dp0backend" && echo Starting Flask server... && echo Server running on http://localhost:5000 && "!PYTHON_EXE!" app.py"

timeout /t 2 /nobreak >nul

REM Start Frontend Server
start "Frontend Server" cmd /k "cd /d "%~dp0frontend" && echo Starting Frontend server... && echo Server running on http://localhost:5173 && npm run dev"

echo.
echo Project started successfully!
echo Backend and Frontend are running in new windows.
pause >nul