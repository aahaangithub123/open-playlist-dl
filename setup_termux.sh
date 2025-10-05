#!/data/data/com.termux/files/usr/bin/bash

echo "========================================"
echo "YouTube Music Downloader Setup (Termux)"
echo "========================================"
echo ""

# Update packages
echo "Updating packages..."
pkg update -y
pkg upgrade -y

# Install required packages
echo ""
echo "Installing required packages..."
# Add nodejs for npm run dev
pkg install -y python ffmpeg git nodejs

# Check installations
echo ""
echo "Checking installations..."
python --version
if [ $? -ne 0 ]; then
    echo "[ERROR] Python installation failed!"
    exit 1
fi
echo "[OK] Python is installed"

ffmpeg -version > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "[ERROR] FFmpeg installation failed!"
    exit 1
fi
echo "[OK] FFmpeg is installed"

# Check node/npm
node -v > /dev/null 2>&1 && npm -v > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "[ERROR] NodeJS/NPM installation failed!"
    exit 1
fi
echo "[OK] NodeJS/NPM is installed"

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python packages
echo ""
echo "Installing Python packages..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install requirements!"
    exit 1
fi
echo "[OK] All Python packages installed"

# Install Node packages for frontend
echo ""
echo "Installing Node packages in open-playlist-dl..."
if [ -d "open-playlist-dl" ]; then
    (cd open-playlist-dl && npm install)
    if [ $? -ne 0 ]; then
        echo "[WARNING] Failed to install Node requirements. Frontend may not run."
    fi
    echo "[OK] Node packages installed."
fi


# Create directories
echo ""
echo "Creating directories and default settings..."
mkdir -p data
# Use the Termux-specific path for the default output
DOWNLOAD_PATH="~/storage/shared/Music/YTMusicDownloads"
mkdir -p "$DOWNLOAD_PATH"

echo "[OK] Created data directory"
echo "[OK] Created downloads directory at $DOWNLOAD_PATH"

# --- CRITICAL: Initialize settings.json with the correct Termux path ---
SETTINGS_FILE="data/settings.json"
DEFAULT_SETTINGS='{
    "output_dir": "'$DOWNLOAD_PATH'",
    "audio_quality": "192K",
    "yt_dlp_path": "yt-dlp"
}'

if [ ! -f "$SETTINGS_FILE" ]; then
    echo "$DEFAULT_SETTINGS" > "$SETTINGS_FILE"
    echo "[OK] Initialized default settings with Termux download path."
else
    echo "[INFO] settings.json already exists. Skipping initialization."
fi

# Setup storage access
echo ""
echo "Setting up storage access..."
termux-setup-storage
echo "[OK] Storage access configured"

# Create and make run script executable
RUN_SCRIPT="run_termux.sh"
echo "Creating run script: $RUN_SCRIPT"
cat > $RUN_SCRIPT << 'EOF'
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
EOF

chmod +x $RUN_SCRIPT
echo "[OK] Created and made run script executable: $RUN_SCRIPT"

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "To run the application:"
echo "  ./run_termux.sh"
echo ""
echo "To access from your browser (Termux recommends the URL shown by npm):"
echo "  http://localhost:5000 (Backend)"
echo "  http://localhost:<npm-port> (Frontend)"
echo ""
echo "Optional: Add cookies.txt to the data folder"
echo "for authenticated downloads"
echo ""
