const { app, BrowserWindow } = require('electron');
const path = require('path');
const fs = require('fs');

app.disableHardwareAcceleration(); // vermeidet GLib/GPU Zicken

const SHOULD_SPAWN = !process.env.SKIP_BACKEND_SPAWN && !process.env.BACKEND_URL;

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

  console.log('Loaded env from', process.cwd() + '/.env');
  if (!SHOULD_SPAWN) {
    console.log('[desktop] Skip backend spawn (SKIP_BACKEND_SPAWN/BACKEND_URL set)');
  } else {
    console.log('[desktop] (would spawn backend) — disabled by our CLI runner');
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
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
