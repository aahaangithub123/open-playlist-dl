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
pkg install -y python ffmpeg git

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
echo "[OK] All packages installed"

# Create directories
echo ""
echo "Creating directories..."
mkdir -p data
mkdir -p ~/storage/shared/Music/YTMusicDownloads

echo "[OK] Created data directory"
echo "[OK] Created downloads directory at ~/storage/shared/Music/YTMusicDownloads"

# Setup storage access
echo ""
echo "Setting up storage access..."
termux-setup-storage
echo "[OK] Storage access configured"

# Make run script executable
if [ -f "run_termux.sh" ]; then
    chmod +x run_termux.sh
    echo "[OK] Made run script executable"
fi

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "To run the application:"
echo "  ./run_termux.sh"
echo ""
echo "To access from your browser:"
echo "  http://localhost:5000"
echo ""
echo "Optional: Add cookies.txt to the data folder"
echo "for authenticated downloads"
echo ""