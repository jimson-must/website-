@echo off
setlocal
cd /d "%~dp0"
title RCHE Staff App

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python from python.org and tick "Add Python to PATH".
  pause
  exit /b 1
)

if not exist "venv\Scripts\python.exe" (
  echo First run: creating the virtual environment. This takes a minute.
  python -m venv venv
  if errorlevel 1 ( echo Could not create the virtual environment. & pause & exit /b 1 )
  "venv\Scripts\python.exe" -m pip install --upgrade pip
  "venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 ( echo Install failed. Check your internet connection and run this file again. & pause & exit /b 1 )
)

set RCHE_OPEN_BROWSER=1
"venv\Scripts\python.exe" app.py
pause
