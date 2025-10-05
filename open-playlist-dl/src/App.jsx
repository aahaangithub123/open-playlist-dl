import React, { useState, useEffect, useCallback } from 'react';
import { Settings, Plus, Trash2, Edit2, Check, X, Download, RefreshCw, AlertCircle, Loader } from 'lucide-react';

const API_URL = 'http://localhost:5000/api';
const DATA_REFRESH_INTERVAL = 5000; // 5 seconds - poll for fresh data from the backend

const App = () => {
  const [playlists, setPlaylists] = useState([]);
  const [newPlaylistUrl, setNewPlaylistUrl] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState({
    output_dir: '',
    bitrate: '320',
    info_refresh_interval: '5',
    schedule_enabled: 'true',
    schedule_days: '1',
    schedule_time: '03:00'
  });
  const [logs, setLogs] = useState([]);
  const [syncing, setSyncing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchLogs = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/logs`);
      if (response.ok) {
        const data = await response.json();
        setLogs(data);
      }
    } catch (err) {
      console.error('Error fetching logs:', err);
    }
  }, []);

  const fetchPlaylists = useCallback(async (isBackground = false) => {
    if (!isBackground) setLoading(true); 

    try {
      const response = await fetch(`${API_URL}/playlists`);
      if (!response.ok) throw new Error('Failed to fetch playlists');
      const data = await response.json();
      setPlaylists(data);
      setError(null);

      const isStillDownloading = data.some(p => p.currentSong && p.currentSong.length > 0);
      
      // If no playlist is actively downloading, turn off the global 'syncing' spinner
      if (!isStillDownloading) {
        setSyncing(false);
      }

    } catch (err) {
      console.error('Error fetching playlists:', err);
      if (!isBackground) setError('Failed to connect to server. Make sure the backend is running.');
    } finally {
      if (!isBackground) setLoading(false);
    }
  }, []);

  const fetchSettings = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/settings`);
      if (!response.ok) throw new Error('Failed to fetch settings');
      const data = await response.json();
      setSettings(data);
    } catch (err) {
      console.error('Error fetching settings:', err);
    }
  }, []);

  // 1. Initial Load: Fetch everything once
  useEffect(() => {
    fetchPlaylists(false); 
    fetchSettings();
    fetchLogs(); 
  }, [fetchPlaylists, fetchSettings, fetchLogs]);

  // 2. Continuous Polling: Always active to keep UI fresh
  useEffect(() => {
    const intervalId = setInterval(() => {
      fetchPlaylists(true); // Fetch silently
      fetchLogs(); 
    }, DATA_REFRESH_INTERVAL);

    return () => clearInterval(intervalId);
  }, [fetchPlaylists, fetchLogs]);


  const handleAddPlaylist = async (e) => {
    e.preventDefault();
    if (!newPlaylistUrl.trim()) return;

    setLoading(true);
    
    try {
      const response = await fetch(`${API_URL}/playlists`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: newPlaylistUrl })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to add playlist');
      }
      
      setNewPlaylistUrl('');
      await fetchPlaylists(false); 
      await fetchLogs();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const deletePlaylist = async (id) => {
    if (!window.confirm('Are you sure you want to delete this playlist? This does not delete downloaded files.')) return;
    
    try {
      await fetch(`${API_URL}/playlists/${id}`, { method: 'DELETE' });
      await fetchPlaylists();
      await fetchLogs();
    } catch (err) {
      setError(`Error deleting playlist: ${err.message}`);
    }
  };

  const startEdit = (id, name) => {
    setEditingId(id);
    setEditName(name);
  };

  const saveEdit = async (id) => {
    try {
      await fetch(`${API_URL}/playlists/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: editName })
      });
      
      setEditingId(null);
      await fetchPlaylists();
      await fetchLogs();
    } catch (err) {
      setError(`Error renaming playlist: ${err.message}`);
    }
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditName('');
  };

  const triggerSync = async (id) => {
    setSyncing(true);
    const url = id ? `${API_URL}/sync/${id}` : `${API_URL}/sync`;
    const action = id ? 'playlist' : 'all playlists';
    
    try {
      await fetch(url, { method: 'POST' });
      await fetchLogs();
    } catch (err) {
      setError(`Error starting execution sync for ${action}: ${err.message}`);
      setSyncing(false);
    }
  };

  const updateSettings = async (e) => {
    e.preventDefault();
    try {
      await fetch(`${API_URL}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      
      setShowSettings(false);
      await fetchLogs();
      window.alert('Settings saved. Note: Changes to scheduling or refresh intervals require a BACKEND RESTART to take full effect.');
    } catch (err) {
      setError(`Error saving settings: ${err.message}`);
    }
  };

  if (loading && playlists.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 text-white flex items-center justify-center">
        <div className="text-center">
          <Loader className="w-16 h-16 animate-spin mx-auto mb-4 text-purple-400" />
          <p className="text-xl">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 text-white p-6">
      <script src="https://cdn.tailwindcss.com"></script>
      <style>{`
        .progress-bar-fill {
          transition: width 0.5s ease-in-out;
        }
      `}</style>
      <div className="max-w-7xl mx-auto">
        {error && (
          <div className="bg-red-900/50 border border-red-500 rounded-lg p-4 mb-6 flex items-center gap-3">
            <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0" />
            <div>
              <p className="font-semibold">Connection Error</p>
              <p className="text-sm text-red-200">{error}</p>
            </div>
            <button onClick={() => setError(null)} className="ml-auto text-red-300 hover:text-red-100">
              <X className="w-5 h-5" />
            </button>
          </div>
        )}

        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              YouTube Music Downloader
            </h1>
            <p className="text-gray-400 mt-2">Live-syncing your playlists effortlessly</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => triggerSync(null)}
              disabled={syncing}
              className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 px-6 py-3 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {syncing ? <Loader className="w-5 h-5 animate-spin" /> : <RefreshCw className="w-5 h-5" />}
              {syncing ? 'Syncing...' : 'Sync All Now'}
            </button>
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 px-6 py-3 rounded-lg font-semibold transition-all"
            >
              <Settings className="w-5 h-5" />
              Settings
            </button>
          </div>
        </div>

        {showSettings && (
          <div className="bg-gray-800 rounded-xl p-6 mb-6 shadow-2xl border border-gray-700">
            <h2 className="text-2xl font-bold mb-4 text-purple-400">Settings</h2>
            <form onSubmit={updateSettings} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Output Settings */}
              <div className="lg:col-span-2">
                <label className="block text-sm font-medium text-gray-300 mb-2">Output Directory</label>
                <input type="text" value={settings.output_dir} onChange={(e) => setSettings({ ...settings, output_dir: e.target.value })}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Bitrate</label>
                <select value={settings.bitrate} onChange={(e) => setSettings({ ...settings, bitrate: e.target.value })}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500">
                  <option value="128">128 kbps</option><option value="192">192 kbps</option><option value="256">256 kbps</option><option value="320">320 kbps</option>
                </select>
              </div>

              {/* Schedule Settings */}
              <div className="lg:col-span-3 border-t border-gray-700 pt-4 mt-2">
                <h3 className="text-lg font-semibold text-purple-300 mb-3">Automation Settings</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                     <label className="block text-sm font-medium text-gray-300 mb-2">Run scheduled sync at:</label>
                    <input type="time" value={settings.schedule_time} onChange={(e) => setSettings({ ...settings, schedule_time: e.target.value })}
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500" />
                  </div>
                   <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">UI Refresh Interval (sec)</label>
                    <input type="number" value={settings.info_refresh_interval} onChange={(e) => setSettings({ ...settings, info_refresh_interval: e.target.value })}
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500" min="3" />
                  </div>
                  <div className="flex items-end pb-2">
                    <input type="checkbox" checked={settings.schedule_enabled === 'true'} onChange={(e) => setSettings({ ...settings, schedule_enabled: e.target.checked ? 'true' : 'false' })}
                      className="w-5 h-5 text-purple-600 bg-gray-700 border-gray-600 rounded focus:ring-purple-500" id="schedule-enabled" />
                    <label htmlFor="schedule-enabled" className="ml-3 text-sm font-medium text-gray-300">Enable Scheduled Downloads</label>
                  </div>
                </div>
              </div>

              <div className="lg:col-span-3 mt-4 flex gap-3">
                <button type="submit" className="px-6 py-2 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 rounded-lg font-semibold">Save Settings</button>
                <button type="button" onClick={() => setShowSettings(false)} className="px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg">Cancel</button>
              </div>
            </form>
          </div>
        )}

        {/* Add Playlist */}
        <div className="bg-gray-800 rounded-xl p-6 mb-6 shadow-2xl border border-gray-700">
          <h2 className="text-xl font-bold mb-4 text-purple-400">Add New Playlist</h2>
          <form onSubmit={handleAddPlaylist} className="flex gap-3">
            <input type="url" value={newPlaylistUrl} onChange={(e) => setNewPlaylistUrl(e.target.value)}
              placeholder="Paste YouTube Music playlist URL..." className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500" required />
            <button type="submit" disabled={loading} className="flex items-center gap-2 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 px-6 py-3 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed">
              {loading ? <Loader className="w-5 h-5 animate-spin" /> : <Plus className="w-5 h-5" />} Add
            </button>
          </form>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <h2 className="text-2xl font-bold mb-4 text-purple-400">Playlists ({playlists.length})</h2>
            
            {playlists.length === 0 ? (
              <div className="bg-gray-800 rounded-xl p-12 text-center border border-gray-700">
                <Download className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                <h3 className="text-xl font-semibold text-gray-400 mb-2">No playlists yet</h3>
                <p className="text-gray-500">Add your first YouTube Music playlist to get started</p>
              </div>
            ) : (
              <div className="space-y-4">
                {playlists.map((playlist) => (
                  <div key={playlist.id} className="bg-gray-800 rounded-xl p-6 shadow-xl border border-gray-700 hover:border-purple-500 transition-all">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex-1 min-w-0">
                        {editingId === playlist.id ? (
                           <div className="flex gap-2">
                            <input type="text" value={editName} onChange={(e) => setEditName(e.target.value)}
                              className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-1 focus:outline-none focus:ring-2 focus:ring-purple-500" autoFocus
                              onKeyPress={(e) => e.key === 'Enter' && saveEdit(playlist.id)} />
                            <button onClick={() => saveEdit(playlist.id)} className="text-green-400 hover:text-green-300 p-1"><Check className="w-5 h-5" /></button>
                            <button onClick={cancelEdit} className="text-red-400 hover:text-red-300 p-1"><X className="w-5 h-5" /></button>
                          </div>
                        ) : (
                           <>
                            <h3 className="text-xl font-bold truncate">{playlist.name}</h3>
                            <p className="text-gray-400 text-sm mt-1 truncate">{playlist.url}</p>
                          </>
                        )}
                      </div>
                      <div className="flex gap-2 ml-4 flex-shrink-0">
                        <button onClick={() => triggerSync(playlist.id)} disabled={syncing} className="p-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed" title="Sync Now">
                          <RefreshCw className={`w-4 h-4 ${playlist.currentSong ? 'animate-spin' : ''}`} />
                        </button>
                        <button onClick={() => startEdit(playlist.id, playlist.name)} className="p-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-all" title="Rename"><Edit2 className="w-4 h-4" /></button>
                        <button onClick={() => deletePlaylist(playlist.id)} className="p-2 bg-red-600 hover:bg-red-700 rounded-lg transition-all" title="Delete"><Trash2 className="w-4 h-4" /></button>
                      </div>
                    </div>

                    <div className="mb-3">
                      <div className="flex justify-between text-sm mb-2">
                        <span className="text-gray-400 truncate flex-1">
                          {playlist.currentSong ? (
                            <span className="text-purple-400 font-medium">
                              <span className="inline-block w-2 h-2 bg-purple-400 rounded-full animate-pulse mr-2"></span>
                              Downloading: {playlist.currentSong}
                            </span>
                          ) : playlist.progress === 100 && playlist.total > 0 ? (
                            <span className="text-green-400 font-medium">✓ Complete</span>
                          ) : (
                            'Idle / Awaiting execution sync'
                          )}
                        </span>
                        <span className="font-semibold ml-4 flex-shrink-0">{playlist.downloaded}/{playlist.total} songs</span>
                      </div>
                      <div className="relative w-full h-3 bg-gray-700 rounded-full overflow-hidden">
                        <div className={`progress-bar-fill absolute h-full ${playlist.progress === 100 && playlist.total > 0 ? 'bg-gradient-to-r from-green-500 to-emerald-500' : 'bg-gradient-to-r from-purple-500 to-pink-500'}`}
                          style={{ width: `${playlist.progress}%` }} />
                      </div>
                    </div>

                    {playlist.lastSync && (
                      <div className="text-xs text-gray-500 mt-2">
                        Last info update: {new Date(playlist.lastSync).toLocaleString()}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <h2 className="text-2xl font-bold mb-4 text-purple-400">Activity Log</h2>
            <div className="bg-gray-800 rounded-xl p-4 shadow-xl border border-gray-700 h-[calc(100vh-300px)] overflow-y-auto">
              {logs.length > 0 ? (
                <div className="space-y-2 font-mono text-sm">
                  {logs.map((log, idx) => (
                    <div key={idx} className="border-l-2 border-purple-500 pl-3 py-1 hover:bg-gray-700/50 transition-colors">
                      <span className="text-gray-500">[{log.time}]</span>
                      <span className="ml-2 text-gray-300">{log.message}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-gray-500 py-8">
                  <p>No activity yet...</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
