@echo off
REM Mahiro Bot Setup Script for Windows

echo.
echo ========================================
echo   Mahiro Telegram Bot - Setup
echo ========================================
echo.

REM Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo Detected Python: %PYTHON_VER%

REM Check if using Python 3.14
echo %PYTHON_VER% | findstr /R "3\.14" >nul
if %ERRORLEVEL% EQU 0 (
    echo.
    echo WARNING: Python 3.14 detected!
    echo Python 3.14 requires build tools (Visual C++, Rust) for some packages.
    echo.
    echo RECOMMENDED: Use Python 3.13 instead
    echo Download from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM Install dependencies
echo.
echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to install dependencies!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Create a .env file with your tokens
echo 2. Run: python main.py
echo.
pause
