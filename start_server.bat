@echo off
REM 安装项目依赖包
echo Installing dependencies...
pip install -r requirements.txt

echo.
REM 启动Flask服务器
echo Starting Flask server...
echo Server running on http://localhost:5000
echo.
python ./backend/app.py

REM 暂停以便查看输出结果
pause