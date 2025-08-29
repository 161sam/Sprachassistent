// Electron preload bridge
// Provides a safe, minimal API to the renderer and injects environment config.
const { contextBridge, ipcRenderer } = require('electron');

// Resolve and normalize BACKEND_URL
function resolveBackendUrl() {
  const envUrl = process.env.BACKEND_URL;
  if (envUrl && typeof envUrl === 'string') return envUrl;

  const host = process.env.WS_HOST || '127.0.0.1';
  const port = process.env.WS_PORT || '48232';
  // Server is expected to expose WebSocket under /ws
  return `ws://${host}:${port}/ws`;
}

const BACKEND_URL = resolveBackendUrl();

// Expose simple env getter and platform flags
contextBridge.exposeInMainWorld('electronAPI', {
  // Platform / environment
  isElectron: true,
  platform: process.platform,
  getEnv: (key) => (process.env ? process.env[key] || '' : ''),

  // App info (optional – requires ipcMain handlers if used)
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),

  // Dialogs and window controls
  showErrorDialog: (title, message) => ipcRenderer.invoke('show-error-dialog', title, message),
  showSaveDialog: (options = {}) => ipcRenderer.invoke('show-save-dialog', options),
  minimize: () => ipcRenderer.invoke('minimize'),

  // Event subscriptions from main → renderer
  onClearConversation: (callback) => { try { ipcRenderer.on('clear-conversation', (_e, ...args) => callback?.(...args)); } catch (_) {} },
  onOpenSettings: (callback) => { try { ipcRenderer.on('open-settings', (_e, ...args) => callback?.(...args)); } catch (_) {} },
  onStartRecording: (callback) => { try { ipcRenderer.on('start-recording', (_e, ...args) => callback?.(...args)); } catch (_) {} },
  onStopRecording: (callback) => { try { ipcRenderer.on('stop-recording', (_e, ...args) => callback?.(...args)); } catch (_) {} },
  onOpenAudioSettings: (callback) => { try { ipcRenderer.on('open-audio-settings', (_e, ...args) => callback?.(...args)); } catch (_) {} },
  onOpenLlmSettings: (callback) => { try { ipcRenderer.on('open-llm-settings', (_e, ...args) => callback?.(...args)); } catch (_) {} },
  onBackendLog: (callback) => { try { ipcRenderer.on('backend-log', (_e, ...args) => callback?.(...args)); } catch (_) {} },
  onBackendError: (callback) => { try { ipcRenderer.on('backend-error', (_e, ...args) => callback?.(...args)); } catch (_) {} },
  removeAllListeners: (channel) => { try { ipcRenderer.removeAllListeners(channel); } catch (_) {} },

  // Event requests renderer → main → renderer broadcast
  requestOpenSettings: () => ipcRenderer.invoke('request-open-settings'),
  requestClearConversation: () => ipcRenderer.invoke('request-clear-conversation'),
  requestStartRecording: () => ipcRenderer.invoke('request-start-recording'),
  requestStopRecording: () => ipcRenderer.invoke('request-stop-recording'),
  requestOpenAudioSettings: () => ipcRenderer.invoke('request-open-audio-settings'),
  requestOpenLlmSettings: () => ipcRenderer.invoke('request-open-llm-settings'),

  // DOM ready convenience
  onDomReady: (fn) => {
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
      try { fn(); } catch (_) {}
    } else {
      window.addEventListener('DOMContentLoaded', () => { try { fn(); } catch (_) {} }, { once: true });
    }
  },

  // Notifications (Renderer-side)
  showNotification: (title, body, options = {}) => {
    try {
      if (Notification.permission === 'granted') {
        return new Notification(title, { body, ...options });
      }
      if (Notification.permission !== 'denied') {
        Notification.requestPermission().then((permission) => {
          if (permission === 'granted') new Notification(title, { body, ...options });
        });
      }
      return null;
    } catch (_) { return null; }
  },

  // Local storage helpers (guarded)
  store: {
    get: (key) => { try { return localStorage.getItem(key); } catch (_) { return null; } },
    set: (key, value) => { try { localStorage.setItem(key, value); } catch (_) {} },
    delete: (key) => { try { localStorage.removeItem(key); } catch (_) {} },
    clear: () => { try { localStorage.clear(); } catch (_) {} }
  },

  // Backend URL accessor
  getBackendUrl: () => BACKEND_URL,
});

// Also expose BACKEND_URL as a simple global for convenience
contextBridge.exposeInMainWorld('BACKEND_URL', BACKEND_URL);

// Persist WS host/port hints for frontend fallbacks
try {
  const u = new URL(BACKEND_URL.replace(/^ws(s)?:/, (m, s) => (s ? 'https:' : 'http:')));
  const host = u.hostname || '127.0.0.1';
  const port = u.port || '48232';
  try { localStorage.setItem('wsHost', host); } catch (_) {}
  try { localStorage.setItem('wsPort', String(port)); } catch (_) {}
} catch (e) {
  console.warn('[preload] Could not parse BACKEND_URL:', e?.message || e);
}

// Minimal wsUtils bridge for auth if frontend expects it
try {
  if (!globalThis.wsUtils) {
    globalThis.wsUtils = { getAuthToken: async () => 'dev-token' };
  }
} catch (_) {}
