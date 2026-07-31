@echo off
title VeloxDonate - Realtime Donation System
cd /d "%~dp0"

echo ==================================================
echo   VeloxDonate Realtime Donation System Launcher
echo ==================================================
echo.

if exist "VeloxDonate.exe" (
    echo Starting VeloxDonate...
    start "" "VeloxDonate.exe"
) else if exist "app.py" (
    echo Starting VeloxDonate via Python...
    python app.py
) else (
    echo [ERROR] VeloxDonate executable or app.py not found!
    pause
)
