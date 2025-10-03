import React, { useState, useEffect, useCallback } from 'react';
import { Play, Settings, Plus, Trash2, Edit2, Check, X, Download, RefreshCw, AlertCircle } from 'lucide-react';

const API_URL = 'http://localhost:5000/api';

const App = () => {
  const [playlists, setPlaylists] = useState([]);
  const [newPlaylistUrl, setNewPlaylistUrl] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState({
    output_dir: 'C:\\Music\\Downloads',
    bitrate: '320',
    sync_interval: '60',
    auto_sync: 'false'
  });
  const [logs, setLogs] = useState([]);
  const [syncing, setSyncing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch playlists
  const fetchPlaylists = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/playlists`);
      if (!response.ok) throw new Error('Failed to fetch playlists');
      const data = await response.json();
      setPlaylists(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching playlists:', err);
      setError('Failed to connect to server. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch settings
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

  // Initial load
  useEffect(() => {
    fetchPlaylists();
    fetchSettings();
  }, [fetchPlaylists, fetchSettings]);

  // Auto-refresh playlists every 2 seconds when syncing
  useEffect(() => {
    const interval = setInterval(() => {
      if (syncing || playlists.some(p => p.currentSong)) {
        fetchPlaylists();
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [syncing, playlists, fetchPlaylists]);

  const addLog = (message) => {
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    setLogs(prev => [{ time, message }, ...prev].slice(0, 20));
  };

  const addPlaylist = async () => {
    if (!newPlaylistUrl.trim()) return;
    
    setLoading(true);
    addLog(`Adding playlist: ${newPlaylistUrl}`);
    
    try {
      const response = await fetch(`${API_URL}/playlists`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: newPlaylistUrl })
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to add playlist');
      }
      
      const data = await response.json();
      addLog(`Added: ${data.name} (${data.existing}/${data.total} already downloaded)`);
      setNewPlaylistUrl('');
      await fetchPlaylists();
    } catch (err) {
      addLog(`Error: ${err.message}`);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const deletePlaylist = async (id) => {
    if (!window.confirm('Are you sure you want to delete this playlist?')) return;
    
    try {
      const response = await fetch(`${API_URL}/playlists/${id}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) throw new Error('Failed to delete playlist');
      
      addLog('Deleted playlist');
      await fetchPlaylists();
    } catch (err) {
      addLog(`Error: ${err.message}`);
    }
  };

  const startEdit = (id, name) => {
    setEditingId(id);
    setEditName(name);
  };

  const saveEdit = async (id) => {
    try {
      const response = await fetch(`${API_URL}/playlists/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: editName })
      });
      
      if (!response.ok) throw new Error('Failed to update playlist');
      
      addLog(`Renamed playlist to: ${editName}`);
      setEditingId(null);
      await fetchPlaylists();
    } catch (err) {
      addLog(`Error: ${err.message}`);
    }
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditName('');
  };

  const syncPlaylist = async (id) => {
    setSyncing(true);
    addLog(`Starting sync for playlist ID: ${id}`);
    
    try {
      const response = await fetch(`${API_URL}/sync/${id}`, {
        method: 'POST'
      });
      
      if (!response.ok) throw new Error('Failed to start sync');
      
      addLog('Sync started successfully');
      await fetchPlaylists();
    } catch (err) {
      addLog(`Error: ${err.message}`);
    } finally {
      setTimeout(() => setSyncing(false), 2000);
    }
  };

  const syncAll = async () => {
    setSyncing(true);
    addLog('Starting global sync for all playlists');
    
    try {
      const response = await fetch(`${API_URL}/sync`, {
        method: 'POST'
      });
      
      if (!response.ok) throw new Error('Failed to start sync');
      
      const data = await response.json();
      addLog(data.message);
      await fetchPlaylists();
    } catch (err) {
      addLog(`Error: ${err.message}`);
    } finally {
      setTimeout(() => setSyncing(false), 2000);
    }
  };

  const updateSettings = async () => {
    try {
      const response = await fetch(`${API_URL}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      
      if (!response.ok) throw new Error('Failed to update settings');
      
      addLog('Settings updated successfully');
      setShowSettings(false);
    } catch (err) {
      addLog(`Error: ${err.message}`);
    }
  };

  if (loading && playlists.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 text-white flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-16 h-16 animate-spin mx-auto mb-4 text-purple-400" />
          <p className="text-xl">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Error Banner */}
        {error && (
          <div className="bg-red-900/50 border border-red-500 rounded-lg p-4 mb-6 flex items-center gap-3">
            <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0" />
            <div>
              <p className="font-semibold">Connection Error</p>
              <p className="text-sm text-red-200">{error}</p>
              <p className="text-xs text-red-300 mt-1">Make sure the backend server is running on port 5000</p>
            </div>
            <button onClick={() => setError(null)} className="ml-auto text-red-300 hover:text-red-100">
              <X className="w-5 h-5" />
            </button>
          </div>
        )}

        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              YouTube Music Downloader
            </h1>
            <p className="text-gray-400 mt-2">Sync and download your playlists effortlessly</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={syncAll}
              disabled={syncing}
              className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 px-6 py-3 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-5 h-5 ${syncing ? 'animate-spin' : ''}`} />
              Sync All
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

        {/* Settings Panel */}
        {showSettings && (
          <div className="bg-gray-800 rounded-xl p-6 mb-6 shadow-2xl border border-gray-700">
            <h2 className="text-2xl font-bold mb-4">Settings</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Output Directory</label>
                <input
                  type="text"
                  value={settings.output_dir}
                  onChange={(e) => setSettings({ ...settings, output_dir: e.target.value })}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="/path/to/downloads"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Bitrate</label>
                <select
                  value={settings.bitrate}
                  onChange={(e) => setSettings({ ...settings, bitrate: e.target.value })}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="128">128 kbps</option>
                  <option value="192">192 kbps</option>
                  <option value="256">256 kbps</option>
                  <option value="320">320 kbps</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Sync Interval (minutes)</label>
                <input
                  type="number"
                  value={settings.sync_interval}
                  onChange={(e) => setSettings({ ...settings, sync_interval: e.target.value })}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  min="1"
                />
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.auto_sync === 'true'}
                  onChange={(e) => setSettings({ ...settings, auto_sync: e.target.checked ? 'true' : 'false' })}
                  className="w-5 h-5 text-purple-600 bg-gray-700 border-gray-600 rounded focus:ring-purple-500"
                  id="auto-sync"
                />
                <label htmlFor="auto-sync" className="ml-3 text-sm font-medium text-gray-300">Enable Auto-Sync</label>
              </div>
            </div>
            <div className="mt-6 flex gap-3">
              <button
                onClick={updateSettings}
                className="px-6 py-2 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 rounded-lg font-semibold"
              >
                Save Settings
              </button>
              <button
                onClick={() => setShowSettings(false)}
                className="px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Add Playlist */}
        <div className="bg-gray-800 rounded-xl p-6 mb-6 shadow-2xl border border-gray-700">
          <h2 className="text-xl font-bold mb-4">Add New Playlist</h2>
          <div className="flex gap-3">
            <input
              type="text"
              value={newPlaylistUrl}
              onChange={(e) => setNewPlaylistUrl(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && addPlaylist()}
              placeholder="Paste YouTube Music playlist URL..."
              className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
            <button
              onClick={addPlaylist}
              disabled={loading}
              className="flex items-center gap-2 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 px-6 py-3 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Plus className="w-5 h-5" />
              Add
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Playlists */}
          <div className="lg:col-span-2">
            <h2 className="text-2xl font-bold mb-4">Playlists ({playlists.length})</h2>
            
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
                            <input
                              type="text"
                              value={editName}
                              onChange={(e) => setEditName(e.target.value)}
                              className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-1 focus:outline-none focus:ring-2 focus:ring-purple-500"
                              autoFocus
                              onKeyPress={(e) => e.key === 'Enter' && saveEdit(playlist.id)}
                            />
                            <button onClick={() => saveEdit(playlist.id)} className="text-green-400 hover:text-green-300 p-1">
                              <Check className="w-5 h-5" />
                            </button>
                            <button onClick={cancelEdit} className="text-red-400 hover:text-red-300 p-1">
                              <X className="w-5 h-5" />
                            </button>
                          </div>
                        ) : (
                          <>
                            <h3 className="text-xl font-bold truncate">{playlist.name}</h3>
                            <p className="text-gray-400 text-sm mt-1 truncate">{playlist.url}</p>
                          </>
                        )}
                      </div>
                      <div className="flex gap-2 ml-4 flex-shrink-0">
                        <button
                          onClick={() => syncPlaylist(playlist.id)}
                          disabled={syncing}
                          className="p-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Sync Playlist"
                        >
                          <RefreshCw className={`w-4 h-4 ${playlist.currentSong ? 'animate-spin' : ''}`} />
                        </button>
                        <button
                          onClick={() => startEdit(playlist.id, playlist.name)}
                          className="p-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-all"
                          title="Rename"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => deletePlaylist(playlist.id)}
                          className="p-2 bg-red-600 hover:bg-red-700 rounded-lg transition-all"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    <div className="mb-3">
                      <div className="flex justify-between text-sm mb-2">
                        <span className="text-gray-400 truncate flex-1">
                          {playlist.currentSong ? (
                            <span className="text-purple-400 font-medium">
                              <span className="inline-block w-2 h-2 bg-purple-400 rounded-full animate-pulse mr-2"></span>
                              {playlist.currentSong}
                            </span>
                          ) : playlist.progress === 100 ? (
                            <span className="text-green-400 font-medium">✓ Complete</span>
                          ) : (
                            'Idle'
                          )}
                        </span>
                        <span className="font-semibold ml-4 flex-shrink-0">
                          {playlist.downloaded}/{playlist.total} songs
                        </span>
                      </div>
                      <div className="relative w-full h-3 bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className={`absolute h-full transition-all duration-500 ${
                            playlist.progress === 100 
                              ? 'bg-gradient-to-r from-green-500 to-emerald-500'
                              : 'bg-gradient-to-r from-purple-500 to-pink-500'
                          }`}
                          style={{ width: `${playlist.progress}%` }}
                        />
                      </div>
                      <div className="text-right text-sm text-gray-400 mt-1">
                        {playlist.progress.toFixed(1)}%
                      </div>
                    </div>

                    {playlist.lastSync && (
                      <div className="text-xs text-gray-500 mt-2">
                        Last synced: {new Date(playlist.lastSync).toLocaleString()}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Console Log */}
          <div>
            <h2 className="text-2xl font-bold mb-4">Activity Log</h2>
            <div className="bg-gray-800 rounded-xl p-4 shadow-xl border border-gray-700 h-[calc(100vh-300px)] overflow-y-auto">
              {logs.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <p>No activity yet</p>
                  <p className="text-sm mt-2">Actions will appear here</p>
                </div>
              ) : (
                <div className="space-y-2 font-mono text-sm">
                  {logs.map((log, idx) => (
                    <div key={idx} className="border-l-2 border-purple-500 pl-3 py-1 hover:bg-gray-700/50 transition-colors">
                      <span className="text-gray-500">[{log.time}]</span>
                      <span className="ml-2 text-gray-300">{log.message}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>YouTube Music Downloader v1.0 • Built with Flask & React</p>
          <p className="mt-1">Using yt-dlp for downloads</p>
        </div>
      </div>
    </div>
  );
};

export default App;