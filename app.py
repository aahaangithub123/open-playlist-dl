from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp
import sqlite3
import os
import threading
import time
from datetime import datetime, date
import json
from pathlib import Path

app = Flask(__name__, static_folder='build', static_url_path='')
CORS(app)

# Configuration
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'playlists.db'
COOKIES_PATH = DATA_DIR / 'cookies.txt'
DATA_DIR.mkdir(exist_ok=True)

# Global state
active_downloads = {}
info_thread = None
scheduler_thread = None
last_schedule_run_date = None # Prevents scheduler from running multiple times a day
global_logs = []
MAX_LOGS = 100

def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Playlists table
    c.execute('''CREATE TABLE IF NOT EXISTS playlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        url TEXT NOT NULL UNIQUE,
        total_songs INTEGER DEFAULT 0,
        last_sync TIMESTAMP
    )''')
    
    # Songs table with playlist tags
    c.execute('''CREATE TABLE IF NOT EXISTS songs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        artist TEXT,
        filename TEXT,
        downloaded BOOLEAN DEFAULT 0,
        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Many-to-many relationship: songs to playlists
    c.execute('''CREATE TABLE IF NOT EXISTS playlist_songs (
        playlist_id INTEGER,
        song_id INTEGER,
        FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
        FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
        PRIMARY KEY (playlist_id, song_id)
    )''')
    
    # Settings table
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    conn.commit()
    conn.close()

def get_settings():
    """Get current settings from database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT key, value FROM settings')
    settings = dict(c.fetchall())
    conn.close()
    
    # Default settings
    defaults = {
        'output_dir': str(BASE_DIR / 'downloads'),
        'bitrate': '320',
        'info_refresh_interval': '5',  # New: Fast UI refresh (seconds)
        'schedule_enabled': 'true',     # New: Controls the scheduled download
        'schedule_days': '1',           # New: Run every X days
        'schedule_time': '03:00'        # New: Run at this time
    }
    
    for key, value in defaults.items():
        if key not in settings:
            save_setting(key, value)
            settings[key] = value
    
    return settings

def save_setting(key, value):
    """Save a setting to database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def log_message(message):
    """Add a log message and print to console"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = {'time': timestamp, 'message': message}
    print(f"[{timestamp}] {message}")
    
    global global_logs
    global_logs.append(log_entry)
    global_logs = global_logs[-MAX_LOGS:] 
    return log_entry

def remove_deleted_file(filepath, output_dir):
    """
    Safely delete a file from the disk based on the stored filename.
    Handles common extension variations.
    """
    if not filepath:
        return False
        
    full_path_guess = Path(output_dir) / Path(filepath).name
    
    if full_path_guess.exists():
        try:
            os.remove(full_path_guess)
            log_message(f"Cleanup: Successfully deleted file: {full_path_guess.name}")
            return True
        except OSError as e:
            log_message(f"Error deleting file {full_path_guess.name}: {e}")
            return False
            
    # Fallback: Check if the file exists with a different extension
    base_name, current_ext = os.path.splitext(Path(filepath).name)
    common_extensions = ['.mp3', '.m4a', '.ogg', '.flac', '.webm']
    
    for ext in common_extensions:
        potential_path = Path(output_dir) / f"{base_name}{ext}"
        if potential_path.exists():
            try:
                os.remove(potential_path)
                log_message(f"Cleanup: Successfully deleted file (fallback ext): {potential_path.name}")
                return True
            except OSError as e:
                log_message(f"Error deleting fallback file {potential_path.name}: {e}")
                
    # log_message(f"Cleanup: File not found on disk for deletion (DB name: '{filepath}')")
    return False

# Custom hook to save the filename after download (Restored and fixed)
class YdlLogger:
    def __init__(self, playlist_id, song_id):
        self.playlist_id = playlist_id
        self.song_id = song_id
        self.filename = None

    def debug(self, msg):
        if msg.startswith('[ExtractAudio] Destination: '):
            full_path = msg.split('[ExtractAudio] Destination: ')[1].strip()
            self.filename = os.path.basename(full_path) 
            
            if self.filename:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute('UPDATE songs SET filename = ? WHERE id = ?', (self.filename, self.song_id))
                conn.commit()
                conn.close()

    def warning(self, msg):
        pass

    def error(self, msg):
        log_message(f"YTDL Error: {msg}")

def get_ydl_opts(output_dir, bitrate, playlist_id, song_id):
    """Get yt-dlp options, now accepting IDs for logging hook."""
    opts = {
        # 1. FORCE THE BEST AUDIO AND A COMPATIBLE THUMBNAIL (JPG)
        # Using [format_id=best/best] ensures we get the best audio/video.
        # The key is to add the custom selector 'th_format:jpg' to guarantee a compatible image.
        'format': 'bestaudio/best',
        'postprocessor_args': {
            # Add this to force the thumbnail to be a universally supported format (JPG)
            'SponsorBlock': ['--fix-thumbnail', 'best[ext=jpg]'],
            'EmbedMetadata': ['--embed-metadata'] 
        },
        
        # 'writethumbnail' is needed to download the file before embedding
        'writethumbnail': True, 
        # 'keepvideo' is set to False to clean up the temporary files
        'keepvideo': False, 
        
        # 2. POST-PROCESSING (Simplified and Combined)
        'postprocessors': [
            {
                # A. Convert to MP3
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': bitrate,
            },
            {
                # B. Embed ALL Metadata (Title, Artist, Album Art, etc.)
                # This post-processor handles both tagging and embedding the art.
                'key': 'EmbedMetadata',
                'add_metadata': True,
                'add_infojson': False,
            }
        ],
        
        'outtmpl': os.path.join(output_dir, '%(title)s - %(artist)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'logger': YdlLogger(playlist_id, song_id) 
    }
    
    # ... (Your cookie logic remains the same)
    if COOKIES_PATH.exists():
        opts['cookiefile'] = str(COOKIES_PATH)
    
    return opts
    
def fetch_playlist_info(url):
    """Fetch playlist information without downloading"""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'force_generic_extractor': True # Helps with some playlist types
    }
    
    if COOKIES_PATH.exists():
        opts['cookiefile'] = str(COOKIES_PATH)
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info

def sync_db_with_youtube_info(playlist_id, youtube_info):
    """
    1. Check for locally deleted files and reset 'downloaded' status.
    2. Check for YouTube removals and delete orphaned files/records.
    3. Add new songs from YouTube.
    4. Update total count.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    settings = get_settings()
    output_dir = settings['output_dir']
    
    # 1. Check for locally deleted files (Downloaded=1 but file is MISSING)
    c.execute('''SELECT s.id, s.filename
                 FROM songs s
                 JOIN playlist_songs ps ON s.id = ps.song_id
                 WHERE ps.playlist_id = ? AND s.downloaded = 1''', (playlist_id,))
    
    local_cleanup_count = 0
    for song_id, filename in c.fetchall():
        if filename:
            full_path = Path(output_dir) / filename
            if not full_path.exists():
                # File is gone from disk, reset downloaded status
                c.execute('UPDATE songs SET downloaded = 0 WHERE id = ?', (song_id,))
                local_cleanup_count += 1

    if local_cleanup_count > 0:
        log_message(f"Local cleanup: Reset {local_cleanup_count} songs for playlist ID {playlist_id} because files were manually deleted.")

    # 2. Get current songs linked to this playlist from the database
    c.execute('''SELECT s.id, s.video_id, s.filename
                 FROM songs s
                 JOIN playlist_songs ps ON s.id = ps.song_id
                 WHERE ps.playlist_id = ?''', (playlist_id,))
    db_songs = {video_id: {'id': song_id, 'filename': filename} for song_id, video_id, filename in c.fetchall()}
    db_video_ids = set(db_songs.keys())
    
    # Get fresh songs from YouTube info
    youtube_entries = youtube_info.get('entries', [])
    youtube_video_ids = set(entry.get('id') for entry in youtube_entries if entry.get('id'))
    
    # Identify songs removed from YouTube (DB but not YouTube)
    songs_to_delete = db_video_ids - youtube_video_ids
    
    # Perform YouTube Cleanup (Deletion from DB and Disk)
    deleted_count = 0
    for video_id in songs_to_delete:
        song_data = db_songs[video_id]
        song_id = song_data['id']
        filename = song_data['filename']
        
        # Delete file from disk
        if filename and remove_deleted_file(filename, output_dir):
            deleted_count += 1
        
        # Delete song link and song record from DB
        c.execute('DELETE FROM playlist_songs WHERE playlist_id = ? AND song_id = ?', (playlist_id, song_id))
        c.execute('DELETE FROM songs WHERE id = ?', (song_id,)) 
    
    if deleted_count > 0:
        log_message(f"YouTube cleanup: Deleted {deleted_count} orphaned song records and files for playlist ID {playlist_id}.")
    
    # 3. Add/Link New Songs
    added_count = 0
    for entry in youtube_entries:
        video_id = entry.get('id')
        if not video_id: continue
        
        title = entry.get('title', 'Unknown')
        
        # Check if song exists globally in the songs table
        c.execute('SELECT id, downloaded FROM songs WHERE video_id = ?', (video_id,))
        song = c.fetchone()
        
        if not song:
            # Insert new song
            c.execute('''INSERT INTO songs (video_id, title, downloaded)
                         VALUES (?, ?, ?)''',
                      (video_id, title, 0))
            song_id = c.lastrowid
            added_count += 1
        else:
            song_id = song[0]
            
        # Link song to playlist (INSERT OR IGNORE prevents duplicates)
        c.execute('''INSERT OR IGNORE INTO playlist_songs (playlist_id, song_id)
                     VALUES (?, ?)''', (playlist_id, song_id))
    
    # 4. Update Playlist Total Songs
    total_songs = len(youtube_entries)
    c.execute('UPDATE playlists SET total_songs = ? WHERE id = ?', (total_songs, playlist_id))
    c.execute('UPDATE playlists SET last_sync = ? WHERE id = ?', (datetime.now(), playlist_id))

    conn.commit()
    conn.close()
    
    return total_songs, added_count, deleted_count

@app.route('/')
def serve():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/playlists', methods=['GET'])
def get_playlists():
    """Get all playlists with their download status"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT p.id, p.name, p.url, p.total_songs, p.last_sync,
                 COUNT(DISTINCT CASE WHEN s.downloaded = 1 THEN ps.song_id END) as downloaded
                 FROM playlists p
                 LEFT JOIN playlist_songs ps ON p.id = ps.playlist_id
                 LEFT JOIN songs s ON ps.song_id = s.id
                 GROUP BY p.id''')
    
    playlists = []
    for row in c.fetchall():
        playlist_id = row[0]
        total_songs = row[3]
        downloaded = row[5]
        current_song = active_downloads.get(playlist_id, {}).get('current_song', '')
        
        playlists.append({
            'id': playlist_id,
            'name': row[1],
            'url': row[2],
            'total': total_songs,
            'downloaded': downloaded,
            'currentSong': current_song,
            'progress': round((downloaded / total_songs * 100) if total_songs > 0 else 0, 1),
            'lastSync': row[4]
        })
    
    conn.close()
    return jsonify(playlists)

@app.route('/api/playlists', methods=['POST'])
def add_playlist():
    """Add a new playlist"""
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        # Check if playlist already exists
        conn_check = sqlite3.connect(DB_PATH)
        c_check = conn_check.cursor()
        c_check.execute('SELECT id FROM playlists WHERE url = ?', (url,))
        if c_check.fetchone():
            conn_check.close()
            return jsonify({'error': 'Playlist already exists'}), 400
        conn_check.close()

        # Fetch playlist info
        info = fetch_playlist_info(url)
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Insert playlist
        playlist_name = info.get('title', 'Unknown Playlist')
        total_songs = len(info.get('entries', []))
        
        c.execute('''INSERT INTO playlists (name, url, total_songs, last_sync)
                     VALUES (?, ?, ?, ?)''',
                  (playlist_name, url, total_songs, datetime.now()))
        playlist_id = c.lastrowid
        
        # Add songs to database
        added_count = 0
        
        for entry in info.get('entries', []):
            video_id = entry.get('id')
            title = entry.get('title', 'Unknown')
            
            # Check if song exists
            c.execute('SELECT id, downloaded FROM songs WHERE video_id = ?', (video_id,))
            song = c.fetchone()
            
            if not song:
                # Insert new song
                c.execute('''INSERT INTO songs (video_id, title, downloaded)
                             VALUES (?, ?, ?)''',
                          (video_id, title, 0))
                song_id = c.lastrowid
                added_count += 1
            else:
                song_id = song[0]

            # Link song to playlist
            c.execute('''INSERT OR IGNORE INTO playlist_songs (playlist_id, song_id)
                         VALUES (?, ?)''', (playlist_id, song_id))
        
        conn.commit()
        conn.close()
        
        log_message(f'Added playlist: {playlist_name} ({total_songs} songs found)')
        
        return jsonify({
            'id': playlist_id,
            'name': playlist_name,
            'total': total_songs,
            'added': added_count
        })
        
    except Exception as e:
        log_message(f"Error adding playlist: {str(e)}")
        return jsonify({'error': f"Failed to fetch playlist info. URL might be invalid or access restricted. ({str(e)})"}), 500

@app.route('/api/playlists/<int:playlist_id>', methods=['DELETE'])
def delete_playlist(playlist_id):
    """Delete a playlist"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT name FROM playlists WHERE id = ?', (playlist_id,))
    playlist = c.fetchone()
    
    if not playlist:
        conn.close()
        return jsonify({'error': 'Playlist not found'}), 404
    
    c.execute('DELETE FROM playlists WHERE id = ?', (playlist_id,))
    conn.commit()
    conn.close()
    
    log_message(f'Deleted playlist: {playlist[0]}')
    return jsonify({'success': True})

@app.route('/api/playlists/<int:playlist_id>', methods=['PUT'])
def update_playlist(playlist_id):
    """Update playlist name"""
    data = request.json
    new_name = data.get('name')
    
    if not new_name:
        return jsonify({'error': 'Name is required'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE playlists SET name = ? WHERE id = ?', (new_name, playlist_id))
    conn.commit()
    conn.close()
    
    log_message(f'Renamed playlist to: {new_name}')
    return jsonify({'success': True})

@app.route('/api/sync/<int:playlist_id>', methods=['POST'])
def sync_playlist(playlist_id):
    """(Manual Sync) Sync a specific playlist"""
    # This now only performs the execution step (downloads/deletes)
    thread = threading.Thread(target=download_playlist, args=(playlist_id,), kwargs={'only_info_sync': False})
    thread.daemon = True
    thread.start()
    
    log_message(f'Manual execution sync started for ID {playlist_id}.')
    return jsonify({'success': True, 'message': 'Manual download/delete started'})

@app.route('/api/sync', methods=['POST'])
def sync_all():
    """(Manual Sync) Sync all playlists"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id FROM playlists')
    playlist_ids = [row[0] for row in c.fetchall()]
    conn.close()
    
    for pid in playlist_ids:
        thread = threading.Thread(target=download_playlist, args=(pid,), kwargs={'only_info_sync': False})
        thread.daemon = True
        thread.start()
    
    log_message(f'Manual execution sync started for all {len(playlist_ids)} playlists.')
    return jsonify({'success': True, 'message': f'Syncing {len(playlist_ids)} playlists and checking for downloads'})

def download_playlist(playlist_id, only_info_sync=False):
    """
    Download songs from a playlist. 
    If only_info_sync is True, it only updates DB counters/info and skips downloads.
    If False, it does both info sync and then downloads.
    """
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, url FROM playlists WHERE id = ?', (playlist_id,))
    playlist = c.fetchone()
    conn.close()
    
    if not playlist:
        log_message(f'Error: Playlist ID {playlist_id} not found.')
        return
    
    playlist_name, url = playlist
    
    # --- STEP 1: Always perform an info sync first to ensure DB is current ---
    try:
        youtube_info = fetch_playlist_info(url)
        sync_db_with_youtube_info(playlist_id, youtube_info)
    except Exception as e:
        log_message(f'Error during info sync for ID {playlist_id}: {str(e)}')
        return

    if only_info_sync:
        return
        
    # --- STEP 2: Start actual download/delete process (if not 'only_info_sync') ---
    log_message(f'Starting execution sync (downloads) for: {playlist_name}')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    settings = get_settings()
    output_dir = settings['output_dir']
    bitrate = settings['bitrate']
    
    os.makedirs(output_dir, exist_ok=True)
    
    c.execute('''SELECT s.id, s.video_id, s.title
                 FROM songs s
                 JOIN playlist_songs ps ON s.id = ps.song_id
                 WHERE ps.playlist_id = ? AND s.downloaded = 0''',
              (playlist_id,))
    
    songs_to_download = c.fetchall()
    
    if not songs_to_download:
        log_message(f'All songs already downloaded for: {playlist_name}')
        conn.close()
        return

    for song_id, video_id, title in songs_to_download:
        try:
            active_downloads[playlist_id] = {'current_song': title} 
            
            video_url = f'https://music.youtube.com/watch?v={video_id}'
            opts = get_ydl_opts(output_dir, bitrate, playlist_id, song_id) 
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([video_url])
            
            conn_dl = sqlite3.connect(DB_PATH)
            c_dl = conn_dl.cursor()
            c_dl.execute('UPDATE songs SET downloaded = 1 WHERE id = ?', (song_id,)) 
            conn_dl.commit()
            conn_dl.close()
            
            log_message(f'Downloaded: {title}')
            
        except Exception as e:
            log_message(f'Error downloading {title}: {str(e)}')
            
    if playlist_id in active_downloads:
        del active_downloads[playlist_id]
    
    log_message(f'Completed execution sync for: {playlist_name}')
    conn.close()

# --- NEW: Continuous Information Sync Loop ---
def info_update_loop():
    """Background thread to rapidly update DB info for a responsive UI."""
    while True:
        settings = get_settings()        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id FROM playlists')
        playlist_ids = [row[0] for row in c.fetchall()]
        conn.close()
        
        for pid in playlist_ids:
            # Run info-sync only: no downloads, just counter/cleanup updates
            thread = threading.Thread(target=download_playlist, args=(pid,), kwargs={'only_info_sync': True})
            thread.daemon = True
            thread.start()
        
        try:
            interval_seconds = int(settings.get('info_refresh_interval', '5'))
        except ValueError:
            interval_seconds = 5
            
        wait_time = max(interval_seconds, 3) # Minimum 3 seconds
        time.sleep(wait_time)

# --- NEW: Scheduled Download/Execution Loop ---
def scheduled_download_loop():
    """Background thread to perform the full download/delete sync on a schedule."""
    global last_schedule_run_date
    while True:
        settings = get_settings()
        
        if settings.get('schedule_enabled') == 'true':
            try:
                now = datetime.now()
                today = now.date()
                
                # Avoid running more than once per day
                if last_schedule_run_date == today:
                    time.sleep(60) # Check again in a minute
                    continue

                schedule_time_str = settings.get('schedule_time', '03:00')
                schedule_time = datetime.strptime(schedule_time_str, '%H:%M').time()

                if now.time() >= schedule_time:
                    log_message(f"Scheduler: It's {now.time()}, past scheduled time of {schedule_time}. Triggering full sync.")
                    
                    # Trigger sync all
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute('SELECT id FROM playlists')
                    playlist_ids = [row[0] for row in c.fetchall()]
                    conn.close()
                    
                    for pid in playlist_ids:
                        thread = threading.Thread(target=download_playlist, args=(pid,), kwargs={'only_info_sync': False})
                        thread.daemon = True
                        thread.start()
                    
                    last_schedule_run_date = today # Mark as run for today
                    log_message(f"Scheduler: Full sync triggered for {len(playlist_ids)} playlists. Next run tomorrow after {schedule_time_str}.")

            except Exception as e:
                log_message(f"Error in scheduler loop: {e}")
        
        time.sleep(60) # Check conditions every minute

def start_background_threads():
    """Start all perpetual background threads."""
    global info_thread, scheduler_thread
    
    if info_thread is None or not info_thread.is_alive():
        log_message("Starting continuous info update loop.")
        info_thread = threading.Thread(target=info_update_loop)
        info_thread.daemon = True
        info_thread.start()
        
    if scheduler_thread is None or not scheduler_thread.is_alive():
        log_message("Starting scheduled download loop.")
        scheduler_thread = threading.Thread(target=scheduled_download_loop)
        scheduler_thread.daemon = True
        scheduler_thread.start()

# API for logs
@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get recent activity logs (reverse chronological)"""
    global global_logs
    return jsonify(global_logs[::-1])

@app.route('/api/settings', methods=['GET'])
def get_settings_api():
    """Get current settings"""
    settings = get_settings()
    return jsonify(settings)

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update settings"""
    data = request.json
    
    for key, value in data.items():
        save_setting(key, str(value))
    
    log_message('Settings updated')
    return jsonify({'success': True})

if __name__ == '__main__':
    init_db()
    start_background_threads()
    print("Starting YouTube Music Downloader...")
    print(f"Database: {DB_PATH}")
    print(f"Cookies: {COOKIES_PATH if COOKIES_PATH.exists() else 'Not found'}")
    # IMPORTANT: use_reloader=False is mandatory for threading
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
