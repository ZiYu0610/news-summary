@echo off
chcp 65001 >nul
title AI新闻日报系统

cd /d "%~dp0"

echo ========================================
echo   AI 行业新闻日报系统
echo   每天自动生成时政 + AIGC行业日报
echo ========================================
echo.

:: 检查API Key
python -c "import os; key=os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('ANTHROPIC_AUTH_TOKEN',''); exit(0 if key else 1)"
if %errorlevel% neq 0 (
    echo [警告] 未检测到 ANTHROPIC_API_KEY
    echo 请在系统环境变量中设置，或先执行:
    echo    set ANTHROPIC_API_KEY=你的密钥
    echo.
)

echo [1] 立即生成今日日报
echo [2] 启动调度模式（每天9:00自动运行）
echo [3] 启动HTTP服务查看历史日报
echo [4] 安装Windows任务计划（需管理员）
echo [5] 退出
echo.

choice /c 12345 /n /m "请选择 (1-5): "

if errorlevel 5 exit /b
if errorlevel 4 goto install
if errorlevel 3 goto serve
if errorlevel 2 goto schedule
if errorlevel 1 goto run

:run
echo.
echo 正在生成日报...
python main.py --init-data
if %errorlevel% equ 0 (
    echo.
    echo ✅ 日报生成完成！
    start "" data\reports\
)
pause
exit /b

:schedule
echo.
echo 启动调度模式（保持窗口打开）...
python main.py --schedule
pause
exit /b

:serve
echo.
echo 启动HTTP服务...
start http://localhost:8000/data/reports/
python -m http.server 8000 -d .
pause
exit /b

:install
echo.
echo 正在注册Windows任务计划（需管理员权限）...
python main.py --install
pause
exit /b
