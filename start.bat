@echo off
cd /d "%~dp0"

:: 1. 启动后台服务 (调用免安装便携 Python 运行时)
start /B "" ".\python_runtime\python.exe" app.py

:: 2. 等待后台服务启动
timeout /t 2 /nobreak >nul

:: 3. 调用系统默认浏览器打开界面
start http://127.0.0.1:8000

exit