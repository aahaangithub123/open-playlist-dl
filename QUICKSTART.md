# Quick Start Guide

## For Windows Users

### Step 1: Install Prerequisites
1. Install **Python 3.8+** from [python.org](https://www.python.org/downloads/)
   - ✅ Check "Add Python to PATH" during installation
2. Install **FFmpeg** from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Extract and add to PATH, or use: `winget install ffmpeg`

### Step 2: Setup Project
1. Download all project files to a folder (e.g., `C:\YTMusicDownloader`)
2. Double-click `setup_windows.bat`
3. Wait for installation to complete

### Step 3: Run
1. Double-click `run_windows.bat`
2. Open browser to `http://localhost:5000`

---

## For Termux (Android) Users

### Step 1: Install Termux
- Download from [F-Droid](https://f-droid.org/packages/com.termux/) (recommended)
- Or Google Play Store

### Step 2: Setup
```bash
# Grant storage permission
termux-setup-storage

# Navigate to project directory
cd ~/storage/shared
mkdir YTMusicDownloader
cd YTMusicDownloader

# Copy all project files here, then run:
chmod +x setup_termux.sh
./setup_termux.sh
```

### Step 3: Run
```bash
chmod +x run_termux.sh
./run_termux.sh
```

Open browser to `http://localhost:5000`

---

## Project File Structure

```
your-project-folder/
├── app.py                  # Main backend server
├── requirements.txt        # Python dependencies
├── setup_windows.bat       # Windows setup script
├── run_windows.bat         # Windows run script
├── setup_termux.sh         # Termux setup script
├── run_termux.sh          # Termux run script
├── README.md              # Full documentation
├── QUICKSTART.md          # This file
├── data/                  # Created automatically
│   ├── playlists.db      # SQLite database
│   └── cookies.txt       # Optional: browser cookies
└── downloads/            # Default music folder
```

---

## First Time Usage

1. **Start the server** (see above)
2. **Open browser** to `http://localhost:5000`
3. **Add a playlist**:
   - Go to YouTube Music
   - Open any playlist
   - Copy the URL (looks like: `https://music.youtube.com/playlist?list=...`)
   - Paste in the "Add New Playlist" field
   - Click "Add"
4. **Wait for processing**: The app fetches playlist info
5. **Sync**: Click the refresh icon on the playlist or "Sync All"
6. **Monitor progress**: Watch the progress bar and activity log

---

## Common Issues & Solutions

### "Failed to connect to server"
- **Solution**: Make sure the backend is running (`app.py`)
- Check if port 5000 is available

### "FFmpeg not found"
- **Windows**: Ensure FFmpeg is in PATH or reinstall
- **Termux**: Run `pkg install ffmpeg`

### "Permission denied" (Termux)
- Run `termux-setup-storage` again
- Grant storage permission in Android settings

### Downloads not starting
- Check output directory exists and is writable
- Verify internet connection
- Add cookies.txt if needed for age-restricted content

### "Module not found"
- **Windows**: Make sure virtual environment is activated
- **Termux**: Reinstall requirements: `pip install -r requirements.txt`

---

## Getting Cookies (Optional)

For age-restricted or members-only playlists:

1. Install browser extension "Get cookies.txt"
2. Go to YouTube Music and log in
3. Click extension and export cookies for `music.youtube.com`
4. Save as `data/cookies.txt`
5. Restart the server

---

## Tips

### Optimize Performance
- Set bitrate to 128 or 192 kbps for faster downloads
- Sync one playlist at a time for better control

### Save Storage
- The app automatically deduplicates songs across playlists
- Songs present in multiple playlists are only downloaded once

### Access from Other Devices
- **Windows**: Use your PC's local IP (e.g., `http://192.168.1.100:5000`)
- **Termux**: The run script shows your device IP

### Schedule Auto-Sync
- Enable "Auto-Sync" in settings
- Set sync interval (e.g., 60 minutes)
- App will automatically check for new songs

---

## Support

If you encounter issues:
1. Check the activity log in the web interface
2. Review the console where `app.py` is running
3. Verify all prerequisites are installed correctly
4. Make sure you're using YouTube Music URLs (not regular YouTube)

---

## Next Steps

- Read full documentation in `README.md`
- Explore settings for customization
- Add multiple playlists
- Set up auto-sync for hands-free operation

Enjoy your music! 🎵
