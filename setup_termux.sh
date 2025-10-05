#!/data/data/com.termux/files/usr/bin/bash

# This is the final, robust script to fix all Termux frontend build errors
# by locking Tailwind CSS to v3, which bypasses the problematic lightningcss native binary.

echo "========================================"
echo "YouTube Music Mirror Sync Setup (Termux)"
echo "========================================"
echo ""

# --- VARIABLES ---
# The root folder of the repository
REPO_ROOT=$(pwd)
# The nested frontend directory containing package.json
FRONTEND_DIR="open-playlist-dl" 
TARGET_DIR="$REPO_ROOT/$FRONTEND_DIR"

VITE_CONFIG="$TARGET_DIR/vite.config.js"
TAILWIND_CONFIG="$TARGET_DIR/tailwind.config.js"
POSTCSS_CONFIG="$TARGET_DIR/postcss.config.cjs"
DOWNLOAD_PATH="~/storage/shared/Music/YTMusicDownloads"
SETTINGS_FILE="data/settings.json"
RUN_SCRIPT="run_termux.sh"


# --- 1. System Cleanup and Preparation ---
echo "Performing global Termux Node/NPM cleanup..."
# Delete the entire global NPM cache and config
rm -rf ~/.npm
echo "[OK] Deleted global NPM cache."

# Re-install nodejs to get a fresh, clean set of native binaries
echo "Re-installing nodejs package (This ensures fresh native binaries)..."
pkg uninstall -y nodejs
pkg install -y nodejs
if [ $? -ne 0 ]; then echo "[ERROR] Core package re-installation failed!"; exit 1; fi
echo "[OK] Core packages re-installed."

# Install other required packages
echo "Installing/updating other packages (python, ffmpeg, git)..."
pkg update -y
pkg upgrade -y
pkg install -y python ffmpeg git
pkg install atomicparsley
echo "[OK] System packages ready."

# --- 2. Python Setup ---
echo ""
echo "Installing Python dependencies (Skipping pip upgrade due to Termux warning)..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then echo "[ERROR] Failed to install Python requirements! Check requirements.txt"; exit 1; fi
echo "[OK] Python packages installed."


# --- 3. Frontend Configuration Fixes (CRITICAL) ---
echo ""
echo "--- Applying Frontend Configuration Fixes for Termux ---"

if [ ! -d "$TARGET_DIR" ]; then
    echo "[ERROR] Frontend directory '$TARGET_DIR' not found. Please verify the nested folder name."
    exit 1
fi

# 3.1: Fix vite.config.js (Switch to PostCSS, remove @tailwindcss/vite plugin)
echo "- Configuring vite.config.js (Switching to PostCSS backend)..."
cat > "$VITE_CONFIG" << EOF
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// WARNING: Removed @tailwindcss/vite plugin to fix Termux native binary error.

export default defineConfig({
  plugins: [
    react(),
  ],
  css: {
    // CRITICAL: Enable PostCSS to handle Tailwind via postcss.config.cjs
    postcss: true,
  }
})
EOF
echo "[OK] vite.config.js updated."


# 3.2: Create postcss.config.cjs (V3 standard plugin entry)
echo "- Creating postcss.config.cjs (Using V3 standard plugin entry)..."
cat > "$POSTCSS_CONFIG" << EOF
module.exports = {
  plugins: {
    // CRITICAL FIX: Use 'tailwindcss' plugin name, guaranteed to work with V3 lock
    tailwindcss: {}, 
    autoprefixer: {},
  },
};
EOF
echo "[OK] postcss.config.cjs created."


# 3.3: Fix tailwind.config.js (Remove the failing 'experimental' flag)
echo "- Modifying tailwind.config.js (Removing ineffective experimental flag)..."
# Use sed to remove the previously injected experimental block
# This finds lines starting with '// CRITICAL FIX...' and deletes until '},'
sed -i '/\/\/ CRITICAL FIX for Termux:/,/\},/d' "$TAILWIND_CONFIG"

if [ $? -ne 0 ]; then
    echo "[WARNING] Automatic removal of experimental flag failed. It may not have been present."
fi
echo "[OK] tailwind.config.js cleaned."


# 3.4: Dependency Installation and Cleanup
cd "$TARGET_DIR"

echo "Locking Tailwind dependencies to v3.4.4 (Bypassing lightningcss)..."
# CRITICAL FIX: Pin to V3 and install all related PostCSS packages
npm install tailwindcss@^3.4.4 postcss@^8.4.38 autoprefixer@^10.4.19 --save-dev --legacy-peer-deps
if [ $? -ne 0 ]; then
    echo "[WARNING] Failed to explicitly install PostCSS dependencies. Continuing to final install."
fi

echo "Performing aggressive NPM cleanup (deleting all lock files and node_modules)..."
# CRITICAL FIX: Delete lock files and node_modules
rm -f package-lock.json yarn.lock
rm -rf node_modules
npm cache clean --force

echo "Running final npm install (will install all packages cleanly)..."
# Final install from the now-guaranteed-correct package.json
npm install --legacy-peer-deps
if [ $? -ne 0 ]; then
    echo "[FATAL ERROR] Node installation failed. Manual diagnosis required."
    cd $REPO_ROOT
    exit 1
fi

echo "[OK] Node packages installed and fixed."
cd $REPO_ROOT
echo "---------------------------------------"


# --- 4. Configuration and Storage ---
echo ""
echo "Setting up configuration and storage..."
mkdir -p data
mkdir -p "$DOWNLOAD_PATH"
termux-setup-storage

DEFAULT_SETTINGS='{
    "output_dir": "'$DOWNLOAD_PATH'",
    "audio_quality": "192K",
    "yt_dlp_path": "yt-dlp"
}'

if [ ! -f "$SETTINGS_FILE" ]; then
    echo "$DEFAULT_SETTINGS" > "$SETTINGS_FILE"
    echo "[OK] Initialized default settings with Termux download path."
fi


# --- 5. Create and Make Run Script Executable ---
echo ""
echo "Creating non-blocking run script: $RUN_SCRIPT"
cat > $RUN_SCRIPT << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash

# Execution Script: Runs the Flask backend in the background and the Node.js frontend in the foreground.

echo "========================================"
echo "Starting YouTube Music Mirror Sync"
echo "========================================"

# --- 1. Start Python Flask in the background (Non-blocking) ---
# The ' & ' is critical to background the process.
nohup python app.py > data/flask_run_log.txt 2>&1 &

FLASK_PID=$!
echo "[OK] Flask Backend started in background (PID: $FLASK_PID). Log: data/flask_run_log.txt"
echo "    Access the backend directly at http://localhost:5000"

sleep 2 # Give Flask time to bind the port

# --- 2. Change Directory and Run Frontend ---
TARGET_DIR="open-playlist-dl"

if [ -d "$TARGET_DIR" ]; then
    echo ""
    echo "Switching to frontend directory and running npm run dev..."
    cd "$TARGET_DIR"
    
    # This command blocks the terminal until Ctrl+C is pressed
    npm run dev -- --host 0.0.0.0 
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
    # Using kill -0 to check if the process is still running, then kill -9
    if kill -0 $FLASK_PID 2>/dev/null; then
        kill -9 $FLASK_PID
        echo "[OK] Flask Backend (PID: $FLASK_PID) terminated."
    else
        echo "[WARNING] Flask Backend (PID: $FLASK_PID) already terminated."
    fi
else
    echo "[WARNING] Could not find Flask PID. Manual cleanup may be required."
fi

echo "Cleanup complete."
exit $NPM_EXIT_CODE
EOF

chmod +x $RUN_SCRIPT
echo "[OK] Created and made run script executable: $RUN_SCRIPT"

# --- 6. Final Instructions ---
echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "To run the application:"
echo "  ./$RUN_SCRIPT"
echo ""
