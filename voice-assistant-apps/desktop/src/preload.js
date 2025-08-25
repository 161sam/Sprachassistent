const { contextBridge, ipcRenderer } = require('electron');
const backendUrl = process.env.BACKEND_URL || 'ws://127.0.0.1:48232/ws';
contextBridge.exposeInMainWorld('BACKEND_URL', backendUrl);

// Sichere API für den Renderer-Prozess
contextBridge.exposeInMainWorld('electronAPI', {
  // App-Informationen
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  
  // Dialog-Funktionen
  showErrorDialog: (title, message) => ipcRenderer.invoke('show-error-dialog', title, message),
  showSaveDialog: () => ipcRenderer.invoke('show-save-dialog'),
  
  // Event Listener für Main-Process Nachrichten
  onClearConversation: (callback) => ipcRenderer.on('clear-conversation', callback),
  onOpenSettings: (callback) => ipcRenderer.on('open-settings', callback),
  onStartRecording: (callback) => ipcRenderer.on('start-recording', callback),
  onStopRecording: (callback) => ipcRenderer.on('stop-recording', callback),
  onOpenAudioSettings: (callback) => ipcRenderer.on('open-audio-settings', callback),
  onBackendLog: (callback) => ipcRenderer.on('backend-log', callback),
  onBackendError: (callback) => ipcRenderer.on('backend-error', callback),
  
  // Event Listener entfernen
  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel),
  
  // Platform-spezifische Informationen
  platform: process.platform,
  isElectron: true,

  getBackendUrl: () => backendUrl,
  onDomReady: (fn) => {
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
      fn();
    } else {
      window.addEventListener('DOMContentLoaded', fn, { once: true });
    }
  },
  
  // Notification API
  showNotification: (title, body, options = {}) => {
    if (Notification.permission === 'granted') {
      return new Notification(title, { body, ...options });
    } else if (Notification.permission !== 'denied') {
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
          return new Notification(title, { body, ...options });
        }
      });
    }
  },
  
  // LocalStorage-Alternative für Electron
  store: {
    get: (key) => {
      return localStorage.getItem(key);
    },
    set: (key, value) => {
      localStorage.setItem(key, value);
    },
    delete: (key) => {
      localStorage.removeItem(key);
    },
    clear: () => {
      localStorage.clear();
    }
  },
  
  // File System (nur lesen, nicht schreiben für Sicherheit)
  readFile: async (filePath) => {
    try {
      const fs = require('fs').promises;
      return await fs.readFile(filePath, 'utf8');
    } catch (error) {
      throw new Error(`Fehler beim Lesen der Datei: ${error.message}`);
    }
  }
});

// Erweiterte API für Desktop-spezifische Features
contextBridge.exposeInMainWorld('desktopAPI', {
  // Fenster-Kontrolle
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),
  
  // System-Integration
  getSystemInfo: () => ({
    platform: process.platform,
    arch: process.arch,
    version: process.version,
    electronVersion: process.versions.electron,
    chromeVersion: process.versions.chrome,
    nodeVersion: process.versions.node
  }),
  
  // Keyboard Shortcuts (bereits im Hauptprozess definiert)
  shortcuts: {
    newConversation: 'CmdOrCtrl+N',
    settings: 'CmdOrCtrl+,',
    startRecording: 'CmdOrCtrl+Enter',
    stopRecording: 'Escape',
    quit: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q'
  }
});

// Console-Weiterleitung für besseres Debugging
const originalConsole = { ...console };
['log', 'warn', 'error', 'info', 'debug'].forEach(method => {
  console[method] = (...args) => {
    originalConsole[method]('[Renderer]', ...args);
  };
});

// --- added: expose ttsPlan API ---

try {
  contextBridge.exposeInMainWorld('ttsPlan', {
    setPlan: (intro, main) => ipcRenderer.invoke('tts-plan:set', { intro, main }),
  });
} catch {}
