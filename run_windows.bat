@echo off
setlocal

echo ========================================
echo YouTube Music Mirror Sync
echo ========================================
echo.

:: --- 1. ACTIVATE PYTHON VENV ---

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo [OK] Python environment activated.
) else (
    echo [WARNING] Virtual environment not found!
    echo Please run setup_windows.bat first.
    pause
    exit /b 1
)

:: --- 2. START FLASK BACKEND NON-BLOCKING ---

if not exist app.py (
    echo [ERROR] app.py not found in the root directory!
    pause
    exit /b 1
)

echo Starting Flask server in the background...

:: Start Flask server and capture its Process ID (PID)
:: /b runs the command without starting a new command prompt window.
:: We use a separate log file to capture its output.
start /b "" python app.py > data\flask_log.txt 2>&1

:: Give Flask a moment to start and grab the PID of the last background task
for /f "tokens=2" %%i in ('tasklist /nh /fi "imagename eq python.exe" /fo csv') do (
    set FLASK_PID=%%~i
    goto :FLASK_STARTED
)

:FLASK_STARTED
echo [OK] Flask Backend initiated. PID: %FLASK_PID%
echo.

:: --- 3. SWITCH TO FRONTEND & RUN NPM DEV ---

set TARGET_DIR=open-playlist-dl
if not exist %TARGET_DIR% (
    echo [ERROR] Target directory '%TARGET_DIR%' not found!
    goto :CLEANUP
)

echo Switching to the frontend development directory: %TARGET_DIR%
cd %TARGET_DIR%

echo.
echo Starting frontend development server (npm run dev)...
echo ========================================
echo Open your browser and go to the address shown by NPM.
echo Press Ctrl+C to stop both servers.
echo ========================================
echo.

:: Execute npm run dev and capture its errorlevel for graceful exit
npm run dev
set NPM_EXIT_CODE=%ERRORLEVEL%

:: The script continues here ONLY when npm run dev is stopped (usually by Ctrl+C)
cd ..

:: --- 4. CLEANUP (Execution after Ctrl+C) ---

:CLEANUP
echo.
echo ========================================
echo Shutting down services...
echo ========================================

:: Terminate the Flask process using the stored PID
if defined FLASK_PID (
    taskkill /PID %FLASK_PID% /F
    echo [OK] Flask Backend (PID: %FLASK_PID%) terminated.
) else (
    echo [WARNING] Could not find Flask PID. Manual cleanup may be required.
)

:: Deactivate venv if it was activated
if defined VIRTUAL_ENV (
    call venv\Scripts\deactivate.bat
)

echo All services shut down.
endlocal
pause
