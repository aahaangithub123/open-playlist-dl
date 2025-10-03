@echo off
echo ========================================
echo YouTube Music Downloader Setup (Windows)
echo ========================================
echo.

:: Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python is installed
echo.

:: Check FFmpeg installation
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] FFmpeg is not installed or not in PATH!
    echo Please install FFmpeg from https://ffmpeg.org/download.html
    echo The program will not work without FFmpeg.
    echo.
    pause
) else (
    echo [OK] FFmpeg is installed
    echo.
)

:: Create virtual environment
echo Creating virtual environment...
if exist venv (
    echo Virtual environment already exists.
) else (
    python -m venv venv
    echo [OK] Virtual environment created
)
echo.

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

:: Install requirements
echo Installing Python packages...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install requirements!
    pause
    exit /b 1
)
echo [OK] All packages installed
echo.

:: Create data directory
if not exist data (
    mkdir data
    echo [OK] Created data directory
)

:: Create downloads directory
if not exist downloads (
    mkdir downloads
    echo [OK] Created downloads directory
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To run the application:
echo   1. Double-click run_windows.bat
echo   2. Or manually: venv\Scripts\activate.bat ^&^& python app.py
echo.
echo Optional: Add cookies.txt to the data folder for authenticated downloads
echo.
pause