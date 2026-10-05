@echo off
title HyperOS Telegram Bot - Feed Test Mode
color 0B
echo ============================================================
echo   Testing APKMirror Feed & App Filters (No Posts Sent)
echo ============================================================
echo.
cd /d "%~dp0"
python main.py --test
echo.
pause
