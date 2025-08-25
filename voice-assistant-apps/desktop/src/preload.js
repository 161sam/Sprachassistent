const { contextBridge } = require('electron');

(function injectWsSettingsFromEnv() {
  try {
    const raw = process.env.BACKEND_URL || 'http://127.0.0.1:48232';
    console.log('[preload] BACKEND_URL', raw);
    const u = new URL(raw);
    const host = u.hostname;
    const port = u.port ? parseInt(u.port, 10) : 48232;

    // Frontend-Defaults überschreiben
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('wsHost', host);
      localStorage.setItem('wsPort', String(port)); // WS = gleicher Port wie HTTP
    }
    // Für Code, der auf window.wsUtils hört
    globalThis.wsUtils = {
      getAuthToken: async () => 'dev-token', // austauschbar mit echter Auth
    };
  } catch (e) {
    console.warn('[preload] Could not parse BACKEND_URL:', e);
  }
})();

// Kleine Bridge, falls mal gebraucht
contextBridge.exposeInMainWorld('electronAPI', { isElectron: true });
