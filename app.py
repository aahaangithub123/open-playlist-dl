from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp
import sqlite3
import os
import threading
import time
from datetime import datetime
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
sync_thread = None
auto_sync_enabled = False

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
        'sync_interval': '60',
        'auto_sync': 'false'
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
    """Add a log message"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {message}")
    return {'time': timestamp, 'message': message}

def get_ydl_opts(output_dir, bitrate):
    """Get yt-dlp options"""
    opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': bitrate,
        }],
        'outtmpl': os.path.join(output_dir, '%(title)s - %(artist)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    if COOKIES_PATH.exists():
        opts['cookiefile'] = str(COOKIES_PATH)
    
    return opts

def fetch_playlist_info(url):
    """Fetch playlist information without downloading"""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }
    
    if COOKIES_PATH.exists():
        opts['cookiefile'] = str(COOKIES_PATH)
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info

@app.route('/')
def serve():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/playlists', methods=['GET'])
def get_playlists():
    """Get all playlists with their download status"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT p.id, p.name, p.url, p.total_songs, p.last_sync,
                 COUNT(DISTINCT ps.song_id) as total_in_db,
                 COUNT(DISTINCT CASE WHEN s.downloaded = 1 THEN ps.song_id END) as downloaded
                 FROM playlists p
                 LEFT JOIN playlist_songs ps ON p.id = ps.playlist_id
                 LEFT JOIN songs s ON ps.song_id = s.id
                 GROUP BY p.id''')
    
    playlists = []
    for row in c.fetchall():
        playlist_id = row[0]
        current_song = active_downloads.get(playlist_id, {}).get('current_song', '')
        
        playlists.append({
            'id': row[0],
            'name': row[1],
            'url': row[2],
            'total': row[3],
            'downloaded': row[6],
            'currentSong': current_song,
            'progress': round((row[6] / row[3] * 100) if row[3] > 0 else 0, 1),
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
        # Fetch playlist info
        info = fetch_playlist_info(url)
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Check if playlist already exists
        c.execute('SELECT id FROM playlists WHERE url = ?', (url,))
        if c.fetchone():
            conn.close()
            return jsonify({'error': 'Playlist already exists'}), 400
        
        # Insert playlist
        playlist_name = info.get('title', 'Unknown Playlist')
        total_songs = len(info.get('entries', []))
        
        c.execute('''INSERT INTO playlists (name, url, total_songs, last_sync)
                     VALUES (?, ?, ?, ?)''',
                  (playlist_name, url, total_songs, datetime.now()))
        playlist_id = c.lastrowid
        
        # Add songs to database
        settings = get_settings()
        output_dir = settings['output_dir']
        
        added_count = 0
        existing_count = 0
        
        for entry in info.get('entries', []):
            video_id = entry.get('id')
            title = entry.get('title', 'Unknown')
            
            # Check if song exists
            c.execute('SELECT id, downloaded FROM songs WHERE video_id = ?', (video_id,))
            song = c.fetchone()
            
            if song:
                song_id = song[0]
                if song[1]:  # If already downloaded
                    existing_count += 1
            else:
                # Insert new song
                c.execute('''INSERT INTO songs (video_id, title, downloaded)
                             VALUES (?, ?, ?)''',
                          (video_id, title, 0))
                song_id = c.lastrowid
                added_count += 1
            
            # Link song to playlist
            c.execute('''INSERT OR IGNORE INTO playlist_songs (playlist_id, song_id)
                         VALUES (?, ?)''', (playlist_id, song_id))
        
        conn.commit()
        conn.close()
        
        log_message(f'Added playlist: {playlist_name} ({existing_count}/{total_songs} already downloaded)')
        
        return jsonify({
            'id': playlist_id,
            'name': playlist_name,
            'total': total_songs,
            'existing': existing_count,
            'added': added_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    """Sync a specific playlist"""
    thread = threading.Thread(target=download_playlist, args=(playlist_id,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'message': 'Sync started'})

@app.route('/api/sync', methods=['POST'])
def sync_all():
    """Sync all playlists"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id FROM playlists')
    playlist_ids = [row[0] for row in c.fetchall()]
    conn.close()
    
    for pid in playlist_ids:
        thread = threading.Thread(target=download_playlist, args=(pid,))
        thread.daemon = True
        thread.start()
    
    return jsonify({'success': True, 'message': f'Syncing {len(playlist_ids)} playlists'})

def download_playlist(playlist_id):
    """Download songs from a playlist"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get playlist info
    c.execute('SELECT name, url FROM playlists WHERE id = ?', (playlist_id,))
    playlist = c.fetchone()
    
    if not playlist:
        conn.close()
        return
    
    playlist_name, url = playlist
    settings = get_settings()
    output_dir = settings['output_dir']
    bitrate = settings['bitrate']
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    log_message(f'Starting sync for: {playlist_name}')
    
    # Get songs to download
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
    
    # Download each song
    for song_id, video_id, title in songs_to_download:
        try:
            active_downloads[playlist_id] = {'current_song': title}
            
            video_url = f'https://music.youtube.com/watch?v={video_id}'
            opts = get_ydl_opts(output_dir, bitrate)
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([video_url])
            
            # Mark as downloaded
            c.execute('UPDATE songs SET downloaded = 1 WHERE id = ?', (song_id,))
            conn.commit()
            
            log_message(f'Downloaded: {title}')
            
        except Exception as e:
            log_message(f'Error downloading {title}: {str(e)}')
    
    # Update last sync
    c.execute('UPDATE playlists SET last_sync = ? WHERE id = ?',
              (datetime.now(), playlist_id))
    conn.commit()
    
    if playlist_id in active_downloads:
        del active_downloads[playlist_id]
    
    log_message(f'Completed sync for: {playlist_name}')
    conn.close()

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
    print("Starting YouTube Music Downloader...")
    print(f"Database: {DB_PATH}")
    print(f"Cookies: {COOKIES_PATH if COOKIES_PATH.exists() else 'Not found'}")
    app.run(host='0.0.0.0', port=5000, debug=True)