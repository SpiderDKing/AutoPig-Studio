@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ===================================================
echo       AutoPig Studio v1.1.0 正在启动中...
echo ===================================================

:: 检查便携 Python 运行时
if exist ".\python_runtime\python.exe" (
    start "" ".\python_runtime\python.exe" app.py
) else (
    start "" python app.py
)

:: 等待后台服务启动
timeout /t 2 /nobreak >nul

:: 调用系统默认浏览器打开纯文本网址
start "" "http://127.0.0.1:8000"

exit