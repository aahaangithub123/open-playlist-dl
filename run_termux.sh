#!/data/data/com.termux/files/usr/bin/bash

echo "========================================"
echo "YouTube Music Downloader"
echo "========================================"
echo ""

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo "[ERROR] app.py not found!"
    echo "Please ensure all files are in the current directory"
    exit 1
fi

# Get local IP address
echo "Getting network information..."
LOCAL_IP=$(ifconfig wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d: -f2)

echo ""
echo "Starting server..."
echo ""
echo "========================================"
echo "Access the app from:"
echo "  This device: http://localhost:5000"
if [ ! -z "$LOCAL_IP" ]; then
    echo "  Other devices: http://$LOCAL_IP:5000"
fi
echo "========================================"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the application
python app.py