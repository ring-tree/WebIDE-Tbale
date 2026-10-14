@echo off
chcp 65001 >nul
REM Project Startup Script
setlocal enabledelayedexpansion

REM ===================== Load Environment =====================
REM 使用系统 Python 读取 env_config.py 中的环境配置
python "%~dp0env_config.py" --export > "%~dp0tmp_env.txt" || (
    echo ERROR: Failed to load env_config.py
    pause
    exit /b 1
)

FOR /F "usebackq tokens=1,* delims==" %%A IN ("%~dp0tmp_env.txt") DO (
    IF "%%A"=="NODE_EXE" SET "NODE_EXE=%%B"
    IF "%%A"=="PYTHON_EXE" SET "PYTHON_EXE=%%B"
)
del "%~dp0tmp_env.txt"

REM ===================== Validation =====================
IF NOT DEFINED NODE_EXE (
    echo ERROR: Failed to load NODE_EXE from env_config.py
    pause
    exit /b 1
)

IF NOT DEFINED PYTHON_EXE (
    echo ERROR: Failed to load PYTHON_EXE from env_config.py
    pause
    exit /b 1
)

IF NOT EXIST "!NODE_EXE!" (
    echo ERROR: Node.js not found at: !NODE_EXE!
    echo Please check env_config.py configuration
    echo Environment test failed.
    pause
    exit /b 1
)

IF NOT EXIST "!PYTHON_EXE!" (
    echo ERROR: Python not found at: !PYTHON_EXE!
    echo Please check env_config.py configuration
    echo Environment test failed.
    pause
    exit /b 1
)

echo ✅ Node.js loaded from env_config.py: !NODE_EXE!
echo ✅ Python loaded from env_config.py: !PYTHON_EXE!

REM ===================== Setup Environment =====================
REM 添加 Node.js 目录到 PATH
FOR %%F IN ("!NODE_EXE!") DO SET "NODE_DIR=%%~dpF"
SET "PATH=!NODE_DIR!;%PATH%"

REM ===================== Start Services =====================
REM 安装前端依赖
cd /d "%~dp0frontend"
IF NOT EXIST "node_modules" (
    echo Installing frontend dependencies...
    npm install
)

REM 启动后端服务
start "Backend Server" cmd /k "cd /d "%~dp0backend" && echo Starting Flask server... && echo Server running on http://localhost:5000 && "!PYTHON_EXE!" app.py"

timeout /t 2 /nobreak >nul

REM 启动前端服务
start "Frontend Server" cmd /k "cd /d "%~dp0frontend" && echo Starting Frontend server... && echo Server running on http://localhost:5173 && npm run dev"

echo.
echo Project started successfully!
echo Backend and Frontend are running in new windows.
pause >nul
