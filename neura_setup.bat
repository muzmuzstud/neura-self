@echo off
setlocal enabledelayedexpansion
title NeuraSelf-UwU Setup
cd /d "%~dp0"
chcp 65001 >nul

set "PYTHON_VER=3.10.11"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VER%/python-%PYTHON_VER%-amd64.exe"

color 0B
echo.
echo  [SYSTEM] Initializing NeuraSelf-UwU Auto-Setup...
echo.

py -3.10 --version >nul 2>&1
if !errorlevel! neq 0 (
    echo  [!] Python 3.10 not found. Starting Auto-Installation...
    echo  [#] Downloading Python Installer...
    curl -L -o py_inst.exe %PYTHON_URL%
    if !errorlevel! neq 0 (
        echo  [X] Download failed. Please install Python 3.10 manually.
        pause
        exit /b 1
    )
    echo  [#] Installing Python - quiet mode...
    start /wait py_inst.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del py_inst.exe
    echo  [OK] Python installation completed.
) else (
    echo  [OK] Python 3.10 already installed.
)

echo  [#] Environment verified. Handing over to Neura Wizard...
timeout /t 2 >nul
py -3.10 neura_setup.py
exit /b 0
