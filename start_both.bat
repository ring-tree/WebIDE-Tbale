@echo off
REM 项目环境初始化脚本

REM 设置项目内 Node.js 路径
SET NODE_DIR=%~dp0node_env
SET PATH=%NODE_DIR%;%PATH%

REM 检查 Node.js 是否存在项目目录中
IF NOT EXIST "%NODE_DIR%\node.exe" (
    echo Error: Portable Node.js not found at %NODE_DIR%\node.exe
    echo Please download and extract Node.js binaries to the node_env folder
    pause
    exit /b 1
)

REM 检查并激活 Python 虚拟环境
IF EXIST "%~dp0backend\.venv\Scripts\activate.bat" (
    call %~dp0backend\.venv\Scripts\activate.bat
    echo Python virtual environment activated
) ELSE (
    echo Warning: Python virtual environment not found at backend\.venv
)

REM 检查前端依赖是否已安装
cd /d %~dp0frontend
IF NOT EXIST "node_modules" (
    echo Installing frontend dependencies...
    npm install
)

REM 回到根目录
cd /d %~dp0

REM 启动后端 Flask 服务器（新窗口中）
start "Backend Server" cmd /k "cd /d %~dp0backend && echo Starting Flask server... && echo Server running on http://localhost:5000 && python app.py"

REM 等待片刻以确保后端已启动
timeout /t 3 /nobreak >nul

REM 启动前端 Vite 服务器（新窗口中）
start "Frontend Server" cmd /k "cd /d %~dp0frontend && echo Starting Frontend server... && echo Server running on http://localhost:5173 && npm run dev"