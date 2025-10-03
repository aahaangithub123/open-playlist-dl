# YouTube Music Playlist Downloader

A modern, beautiful WebUI for downloading and syncing YouTube Music playlists using yt-dlp.

## Features

- ✨ Modern, beautiful WebUI with real-time progress tracking
- 📊 Individual progress bars for each playlist
- 🎵 Smart song deduplication across playlists
- 🔄 Global and per-playlist sync
- ⚙️ Configurable settings (output directory, bitrate, auto-sync)
- 📝 Real-time activity log
- 🍪 Automatic cookie support
- 💾 SQLite database for tracking downloads
- 🎨 Responsive design for desktop and mobile

## Prerequisites

### Windows
1. **Python 3.8+** - Download from [python.org](https://www.python.org/downloads/)
2. **FFmpeg** - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Add FFmpeg to your PATH environment variable

### Termux (Android)
1. Install Termux from F-Droid (recommended) or Google Play
2. Update packages:
   ```bash
   pkg update && pkg upgrade
   ```
3. Install required packages:
   ```bash
   pkg install python ffmpeg
   ```

## Installation

### Windows

1. **Clone or download this project**
   ```cmd
   git clone https://github.com/aahaangithub123/open-playlist-dl
   cd open-playlist-dl
   ```

2. **Create a virtual environment** (recommended)
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install Python dependencies**
   ```cmd
   pip install -r requirements.txt
   ```

4. **Create data directory**
   ```cmd
   mkdir data
   ```

5. **(Optional) Add cookies for age-restricted content**
   - Export cookies from your browser using an extension like "Get cookies.txt"
   - Save the cookies.txt file to the `data` folder

6. **Run the application**
   ```cmd
   python app.py
   ```

7. **Open your browser**
   - Navigate to `http://localhost:5000`

### Termux (Android)

1. **Navigate to storage**
   ```bash
   termux-setup-storage
   cd ~/storage/shared
   ```

2. **Create project directory**
   ```bash
   mkdir open-playlist-dl
   cd open-playlist-dl
   ```

3. **Create and save the app.py file**
   - Use a text editor or copy the file
   ```bash
   nano app.py
   # Paste the content and save (Ctrl+X, Y, Enter)
   ```

4. **Create requirements.txt**
   ```bash
   nano requirements.txt
   # Paste the requirements and save
   ```

5. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

6. **Create data directory**
   ```bash
   mkdir data
   ```

7. **(Optional) Add cookies**
   ```bash
   # Copy your cookies.txt to data folder
   cp /path/to/cookies.txt data/
   ```

8. **Run the application**
   ```bash
   python app.py
   ```

9. **Access from your device**
   - Open a browser on your Android device
   - Go to `http://localhost:5000`
   - Or from another device on the same network: `http://<your-phone-ip>:5000`

## Usage

### Adding a Playlist

1. Copy a YouTube Music playlist URL
   - Example: `https://music.youtube.com/playlist?list=PLxxxxxxxxxxxxxx`
2. Paste it in the "Add New Playlist" field
3. Click "Add" - the playlist will be fetched and added to your list
4. The system will automatically detect songs already downloaded

### Managing Playlists

- **Rename**: Click the edit (pencil) icon
- **Delete**: Click the trash icon
- **Sync Individual**: Click the refresh icon on a playlist
- **Sync All**: Click "Sync All" button in the header

### Settings

Click the "Settings" button to configure:
- **Output Directory**: Where to save downloaded music
  - Windows: `C:\Music\Downloads`
  - Termux: `/storage/emulated/0/Music/Downloads`
- **Bitrate**: Audio quality (128, 192, 256, 320 kbps)
- **Sync Interval**: How often to auto-sync (in minutes)
- **Auto-Sync**: Enable/disable automatic synchronization

### Understanding Progress

Each playlist shows:
- **Song Counter**: `23/50` means 23 downloaded out of 50 total
- **Progress Bar**: Visual representation of completion percentage
- **Current Song**: Name of the song currently being downloaded
- **Status**: Real-time updates in the activity log

### Activity Log

The right sidebar shows recent activity:
- Playlist additions
- Download progress
- Completion notifications
- Errors (if any)

## How It Works

### Database Structure

The application uses SQLite with three main tables:

1. **playlists**: Stores playlist information
2. **songs**: Stores unique songs with video IDs
3. **playlist_songs**: Many-to-many relationship (songs can be in multiple playlists)

### Smart Deduplication

When you add a playlist:
1. System fetches all songs from the playlist
2. Compares each song's video ID with the database
3. If song exists and is downloaded → counts toward completion
4. If song exists but not downloaded → queued for download
5. If song is new → added to database and queued

This means if Song A is in Playlist 1 and Playlist 2:
- It only downloads once
- Both playlists show it as downloaded
- Storage is optimized

### Sync Process

**Global Sync**: Downloads all missing songs from all playlists
**Playlist Sync**: Downloads only missing songs from that specific playlist

The sync process:
1. Queries database for songs marked as "not downloaded"
2. Uses yt-dlp to download each song
3. Converts to MP3 with specified bitrate
4. Updates database when complete
5. Shows real-time progress

## Troubleshooting

### Windows Issues

**"FFmpeg not found"**
- Ensure FFmpeg is installed and added to PATH
- Restart command prompt after adding to PATH

**"Module not found" errors**
- Ensure virtual environment is activated
- Reinstall requirements: `pip install -r requirements.txt`

**Permission errors**
- Run as administrator if saving to system directories
- Or change output directory to user folder

### Termux Issues

**"Permission denied" for storage**
- Run `termux-setup-storage` again
- Grant storage permission in Android settings

**"Cannot connect to server"**
- Check if Python is running without errors
- Try accessing `http://127.0.0.1:5000` instead

**Download failures**
- Ensure you have stable internet connection
- Check if cookies.txt is needed for age-restricted content
- Update yt-dlp: `pip install --upgrade yt-dlp`

### General Issues

**Playlist not loading**
- Verify the URL is correct (YouTube Music, not regular YouTube)
- Check internet connection
- Try adding cookies.txt for authentication

**Songs not downloading**
- Check output directory exists and is writable
- Verify FFmpeg is working: `ffmpeg -version`
- Check activity log for specific errors

**Database errors**
- Delete `data/playlists.db` and restart (will reset all data)
- Ensure data directory has write permissions

## Advanced Configuration

### Cookies for Authentication

Some playlists or songs may require authentication. To add cookies:

1. Install a browser extension like "Get cookies.txt"
2. Log into YouTube Music
3. Export cookies for `music.youtube.com`
4. Save as `data/cookies.txt`
5. Restart the application

### Custom Output Templates

Edit the `get_ydl_opts` function in `app.py`:

```python
'outtmpl': os.path.join(output_dir, '%(title)s - %(artist)s.%(ext)s'),
```

Change to your preferred format:
- `'%(title)s.%(ext)s'` - Title only
- `'%(artist)s/%(title)s.%(ext)s'` - Artist folders
- `'%(playlist)s/%(title)s.%(ext)s'` - Playlist folders

### Running as a Service

**Windows**: Use NSSM or Task Scheduler
**Termux**: Use Termux:Boot app

## Project Structure

```
open-playlist-dl/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── data/                  # Data directory
│   ├── playlists.db      # SQLite database
│   └── cookies.txt       # (Optional) Browser cookies
└── downloads/            # Default output directory
```

## API Endpoints

If you want to integrate with other tools:

- `GET /api/playlists` - Get all playlists
- `POST /api/playlists` - Add new playlist
- `DELETE /api/playlists/<id>` - Delete playlist
- `PUT /api/playlists/<id>` - Update playlist name
- `POST /api/sync/<id>` - Sync specific playlist
- `POST /api/sync` - Sync all playlists
- `GET /api/settings` - Get settings
- `POST /api/settings` - Update settings

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is for personal use. Respect YouTube's Terms of Service and copyright laws.

## Credits

- Built with Flask and React
- Uses yt-dlp for downloading
- FFmpeg for audio conversion
- SQLite for data management

