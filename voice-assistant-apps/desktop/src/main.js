const { app, BrowserWindow, Menu, dialog, shell, Tray, nativeImage, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const log = require('electron-log');
log.info('Desktop app starting');
const { autoUpdater } = require('electron-updater');
const dotenv = require('dotenv');
const http = require('http');
const url = require('url');

app.disableHardwareAcceleration(); // vermeidet GLib/GPU Zicken

// Load .env into process.env for desktop runner
try {
  const envPath = path.resolve(process.cwd(), '.env');
  dotenv.config({ path: envPath });
  log.info('Loaded .env from', envPath);
} catch (e) {
  log.warn('Could not load .env:', e?.message || e);
}

const SHOULD_SPAWN = !process.env.SKIP_BACKEND_SPAWN && !process.env.BACKEND_URL;

// ----------------------------- IPC Handlers ------------------------------
// Provide minimal handlers used by the preload/renderer

// App version
ipcMain.handle('get-app-version', async () => app.getVersion());

// Error dialog (returns response index)
ipcMain.handle('show-error-dialog', async (event, title, message) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  const opts = {
    type: 'error',
    title: title || 'Fehler',
    message: title || 'Fehler',
    detail: message || '',
    buttons: ['OK']
  };
  const res = await dialog.showMessageBox(win || null, opts);
  return { response: res.response, checkboxChecked: !!res.checkboxChecked };
});

// Save dialog (returns file path)
ipcMain.handle('show-save-dialog', async (event, options = {}) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  const defaultOptions = {
    title: 'Speichern unter',
    buttonLabel: 'Speichern',
    properties: ['createDirectory', 'showOverwriteConfirmation'],
    filters: options.filters || [
      { name: 'JSON', extensions: ['json'] },
      { name: 'Audio', extensions: ['wav', 'mp3', 'ogg'] },
      { name: 'Alle Dateien', extensions: ['*'] }
    ]
  };
  const res = await dialog.showSaveDialog(win || null, { ...defaultOptions, ...options });
  return { canceled: res.canceled, filePath: res.filePath || '' };
});

// Minimize window
ipcMain.handle('minimize', async (event) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  if (win) { win.minimize(); return true; }
  return false;
});

// --------------------------- Window References ---------------------------
let mainWindow = null;

function sendToRenderer(channel, ...args) {
  const win = BrowserWindow.getFocusedWindow() || mainWindow;
  if (win && !win.isDestroyed()) {
    win.webContents.send(channel, ...args);
    return true;
  }
  return false;
}

// Request handlers to dispatch events to renderer
ipcMain.handle('request-open-settings', async () => sendToRenderer('open-settings'));
ipcMain.handle('request-clear-conversation', async () => sendToRenderer('clear-conversation'));
ipcMain.handle('request-start-recording', async () => sendToRenderer('start-recording'));
ipcMain.handle('request-stop-recording', async () => sendToRenderer('stop-recording'));
ipcMain.handle('request-open-audio-settings', async () => sendToRenderer('open-audio-settings'));
ipcMain.handle('request-open-llm-settings', async () => sendToRenderer('open-llm-settings'));

function resolveGuiIndex() {
  const candidates = [
    path.resolve(__dirname, '..', '..', 'shared', 'index.html'),                           // voice-assistant-apps/shared/index.html
    path.resolve(__dirname, '..', 'shared', 'index.html'),                                 // desktop/shared/index.html (falls es das doch mal gibt)
    path.resolve(process.cwd(), 'voice-assistant-apps', 'shared', 'index.html'),           // CWD/voice-assistant-apps/shared/index.html
    path.resolve(process.cwd(), 'shared', 'index.html'),                                   // CWD/shared/index.html (fallback)
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  // Zur Not: zeig eine kurze Inline-Seite an
  return null;
}

function createWindow () {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: { preload: path.join(__dirname, 'preload.js') }
  });
  mainWindow = win;
  win.on('closed', () => { if (mainWindow === win) mainWindow = null; });

  console.log('Loaded env from', process.cwd() + '/.env');
  if (!SHOULD_SPAWN) {
    console.log('[desktop] Skip backend spawn (SKIP_BACKEND_SPAWN/BACKEND_URL set)');
  } else {
    // Try to spawn backend (FastAPI adapter via uvicorn)
    try {
      const host = process.env.WS_HOST || process.env.BACKEND_HOST || '127.0.0.1';
      const port = process.env.WS_PORT || process.env.BACKEND_PORT || '48232';
      const py = process.env.PYTHON || 'python3';
      const args = ['-m', 'uvicorn', 'ws_server.transport.fastapi_adapter:app', '--host', host, '--port', String(port)];
      console.log('[desktop] Spawning backend:', py, args.join(' '));
      const childEnv = { ...process.env, ENABLE_TTS: process.env.ENABLE_TTS || '1' };
      const child = spawn(py, args, { cwd: process.cwd(), env: childEnv, stdio: 'pipe' });
      child.stdout.on('data', (d) => console.log('[backend]', d.toString().trim()));
      child.stderr.on('data', (d) => console.warn('[backend]', d.toString().trim()));
      child.on('exit', (code) => console.log('[backend] exited with code', code));
      // Clean up on app quit
      app.on('before-quit', () => { try { child.kill(); } catch (_) {} });
    } catch (e) {
      console.warn('[desktop] Backend spawn failed:', e?.message || e);
    }
  }

  const guiIndex = resolveGuiIndex();
  if (guiIndex) {
    console.log('[desktop] Loading GUI from', guiIndex);
    win.loadFile(guiIndex);
  } else {
    console.warn('[desktop] GUI index.html nicht gefunden – zeige Fallback.');
    win.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(`
      <html><body style="font-family:sans-serif;padding:20px">
        <h1>KI‑Sprachassistent</h1>
        <p><b>index.html</b> nicht gefunden. Erwartet unter <code>voice-assistant-apps/shared/index.html</code>.</p>
      </body></html>`));
  }
}

app.whenReady().then(() => {
  createWindow();
  // Build minimal app menu with action dispatchers
  const template = [
    ...(process.platform === 'darwin' ? [{
      label: app.name,
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' }
      ]
    }] : []),
    {
      label: 'Ansicht',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' }
      ]
    },
    {
      label: 'Aktionen',
      submenu: [
        { label: 'Einstellungen öffnen', accelerator: 'Ctrl+,', click: () => sendToRenderer('open-settings') },
        { type: 'separator' },
        { label: 'Aufnahme starten', accelerator: 'Ctrl+F', click: () => sendToRenderer('start-recording') },
        { label: 'Aufnahme stoppen', accelerator: 'Esc', click: () => sendToRenderer('stop-recording') },
        { type: 'separator' },
        { label: 'Konversation leeren', click: () => sendToRenderer('clear-conversation') },
        { label: 'Audio-Einstellungen', click: () => sendToRenderer('open-audio-settings') },
        { label: 'LLM-Einstellungen', accelerator: 'Ctrl+Shift+L', click: () => sendToRenderer('open-llm-settings') }
      ]
    },
    {
      role: 'help',
      submenu: [
        { label: 'Projektseite', click: async () => { await shell.openExternal('https://example.invalid'); } }
      ]
    }
  ];
  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
