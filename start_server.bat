@echo off
chcp 65001 >nul
REM 安装项目依赖包
echo Installing dependencies...

REM 定义便携式Python环境路径
SET PORTABLE_PYTHON=%~dp0backend\python313\python.exe

REM 检查便携式Python环境
IF NOT EXIST "%PORTABLE_PYTHON%" (
    echo ERROR: Portable Python not found!
    echo Please ensure portable Python exists at:
    echo %PORTABLE_PYTHON%
    pause
    exit /b 1
)

REM 使用项目中的便携式Python环境安装依赖
"%PORTABLE_PYTHON%" -m pip install -r requirements.txt

echo.
REM 切换到backend目录
cd /d %~dp0backend

REM 打印调试信息
echo 当前目录: %cd%
echo 便携式Python路径: %PORTABLE_PYTHON%
if exist "%PORTABLE_PYTHON%" (
    echo 便携式Python存在: yes
) else (
    echo 便携式Python存在: no
)

REM 启动Flask服务器
echo Starting Flask server...
echo Server running on http://localhost:5000
echo.

REM 使用项目中的便携式Python环境启动服务器
"%PORTABLE_PYTHON%" app.py

REM 暂停以便查看输出结果
pause