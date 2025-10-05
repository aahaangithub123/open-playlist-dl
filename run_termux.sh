#!/data/data/com.termux/files/usr/bin/bash

# This script runs the Flask backend in the background and the Node.js frontend in the foreground.

echo "========================================"
echo "Starting YouTube Music Mirror Sync"
echo "========================================"

# --- 1. Start Python Flask in the background (Non-blocking) ---
# We use nohup to ensure Flask keeps running even if the shell closes temporarily,
# and redirect output to a log file.
nohup python app.py > data/flask_run_log.txt 2>&1 &

FLASK_PID=$!
echo "[OK] Flask Backend started in background (PID: $FLASK_PID). Log: data/flask_run_log.txt"
echo "     Access the backend directly at http://localhost:5000"

sleep 2 # Give Flask time to bind the port

# --- 2. Change Directory and Run Frontend ---
TARGET_DIR="open-playlist-dl"

if [ -d "$TARGET_DIR" ]; then
    echo ""
    echo "Switching to frontend directory and running npm run dev..."
    cd "$TARGET_DIR"
    
    # This command blocks the terminal until Ctrl+C is pressed
    npm run dev
    NPM_EXIT_CODE=$?
    
    # Return to root directory
    cd ..
else
    echo ""
    echo "[ERROR] Frontend directory '$TARGET_DIR' not found."
    NPM_EXIT_CODE=1
fi

# --- 3. Cleanup: Kill the Flask process ---
echo ""
echo "========================================"
echo "Shutting down services..."
echo "========================================"

# Kill Flask process using its stored PID
if [ -n "$FLASK_PID" ]; then
    kill -9 $FLASK_PID
    echo "[OK] Flask Backend (PID: $FLASK_PID) terminated."
else
    echo "[WARNING] Could not find Flask PID. Manual cleanup may be required."
fi

echo "Cleanup complete."
exit $NPM_EXIT_CODE
