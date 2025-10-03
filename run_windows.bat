@echo off
echo ========================================
echo YouTube Music Downloader
echo ========================================
echo.

:: Activate virtual environment
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
) else (
    echo [WARNING] Virtual environment not found!
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

:: Check if app.py exists
if not exist app.py (
    echo [ERROR] app.py not found!
    pause
    exit /b 1
)

:: Run the application
echo.
echo Starting server...
echo.
echo ========================================
echo Open your browser and go to:
echo http://localhost:5000
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

python app.py

pause