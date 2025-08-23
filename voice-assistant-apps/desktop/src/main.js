'use strict';

const { app, BrowserWindow, Menu, dialog, shell, Tray, nativeImage, ipcMain } = require('electron');
const path   = require('path');
const fs     = require('fs');
const { spawn } = require('child_process');
const log    = require('electron-log');
const { autoUpdater } = require('electron-updater');
const dotenv = require('dotenv');
const http   = require('http');
const url    = require('url');

// Ping the metrics health endpoint until it responds 200
function waitForHealth(
  urlStr = `http://${process.env.WS_HOST || '127.0.0.1'}:${process.env.METRICS_PORT || '48232'}/health`,
  retries = 120,
  delayMs = 500
) {
  return new Promise((resolve, reject) => {
    const ping = () => {
      const req = http.get(urlStr, (res) => {
        if (res.statusCode === 200) { res.resume(); resolve(); }
        else { res.resume(); (retries-- > 0) ? setTimeout(ping, delayMs) : reject(new Error(`health check failed: ${res.statusCode}`)); }
      });
      req.on('error', () => (retries-- > 0) ? setTimeout(ping, delayMs) : reject(new Error('health check error')));
    };
    ping();
  });
}

// ---- Basics -----------------------------------------------------------------
const isDev = process.env.NODE_ENV === 'development' || process.argv.includes('--dev');
const isMac = process.platform === 'darwin';
const projectRoot = app.isPackaged
  ? path.join(process.resourcesPath, 'app')
  : path.resolve(__dirname, '../../../');

function resolveBackendBinary() {
  // Prefer explicit PYTHON env but fall back to platform defaults.
  const pythonCmd = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
  return { cmd: pythonCmd, args: ['-m', 'ws_server.cli'] };
}

let mainWindow;
let tray;
let backendProcess;
let guiServer;
const guiPort = Number(process.env.GUI_PORT || 48233);

// Logging
log.transports.file.level = 'info';
autoUpdater.logger = log;

// Single Instance
if (!app.requestSingleInstanceLock()) app.quit();
app.on('second-instance', () => {
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show(); mainWindow.focus();
  }
});

// Server-freundliche Flags
app.disableHardwareAcceleration();
app.commandLine.appendSwitch('no-sandbox');
app.commandLine.appendSwitch('disable-setuid-sandbox');
app.commandLine.appendSwitch('disable-dev-shm-usage');

// ---- App lifecycle ----------------------------------------------------------
app.whenReady().then(async () => {
  loadEnv();
  startGuiServer();
  await startBackend();
  createMainWindow();
  createTray();
  if (!isDev && app.isPackaged) autoUpdater.checkForUpdatesAndNotify();
});

app.on('window-all-closed', () => {
  if (!isMac) { stopBackend(); app.quit(); }
});
app.on('before-quit', () => stopBackend());

// ---- Env --------------------------------------------------------------------
function loadEnv() {
  const rootEnv  = path.join(projectRoot, '.env');
  const localEnv = path.join(__dirname, '../.env');
  const envPath  = fs.existsSync(rootEnv) ? rootEnv : localEnv;
  dotenv.config({ path: envPath });
  log.info(`Loaded env from ${envPath}`);
}

// ---- GUI HTTP server --------------------------------------------------------
function startGuiServer() {
  const guiRoot = path.join(projectRoot, 'gui');
  const shared  = path.join(projectRoot, 'voice-assistant-apps', 'shared');
  const mime = {
    '.html':'text/html','.js':'application/javascript','.mjs':'application/javascript',
    '.css':'text/css','.json':'application/json','.png':'image/png','.jpg':'image/jpeg',
    '.jpeg':'image/jpeg','.svg':'image/svg+xml','.ico':'image/x-icon','.wav':'audio/wav',
    '.mp3':'audio/mpeg','.wasm':'application/wasm'
  };
  const safe = p => path.normalize(p).replace(/^(\.\.(\/|\\|$))+/, '');

  guiServer = http.createServer((req, res) => {
    try {
      let reqPath = decodeURIComponent((url.parse(req.url).pathname) || '/');
      if (reqPath === '/') reqPath = '/index.html';
      let filePath = path.join(guiRoot, safe(reqPath));

      // optionaler shared-Ordner
      if (!fs.existsSync(filePath) && reqPath.startsWith('/voice-assistant-apps/shared/')) {
        filePath = path.join(shared, safe(reqPath.replace(/^\/voice-assistant-apps\/shared\//, '')));
      }

      if (!fs.existsSync(filePath)) { res.statusCode = 404; return res.end('Not Found'); }
      res.setHeader('Content-Type', mime[path.extname(filePath)] || 'application/octet-stream');
      fs.createReadStream(filePath).pipe(res);
    } catch (e) {
      res.statusCode = 500; res.end('Server error');
    }
  }).listen(guiPort, '127.0.0.1', () => log.info(`GUI static server: http://127.0.0.1:${guiPort}`));

  guiServer.on('error', (e) => log.error('GUI server error', e));
}

// ---- Main Window ------------------------------------------------------------
function createMainWindow() {
  // Icon
  let iconPath = path.join(projectRoot, 'gui', 'icons', 'icon-512x512.png');
  if (!fs.existsSync(iconPath)) iconPath = path.join(projectRoot, 'gui', 'icons', 'icon.png');

  const preload = path.join(__dirname, 'preload.js');
  const hasPreload = fs.existsSync(preload);

  mainWindow = new BrowserWindow({
    width: 1200, height: 900, minWidth: 800, minHeight: 600,
    show: false, backgroundColor: '#0f0f23',
    icon: fs.existsSync(iconPath) ? iconPath : undefined,
    titleBarStyle: isMac ? 'hiddenInset' : 'default',
    webPreferences: {
      autoplayPolicy: 'no-user-gesture-required',
      contextIsolation: true, nodeIntegration: false,
      sandbox: false, webSecurity: true,
      preload: hasPreload ? preload : undefined
    }
  });

  mainWindow.loadURL(`http://127.0.0.1:${guiPort}/`);

  mainWindow.webContents.on('did-fail-load', (e, code, desc, theUrl) => {
    log.error(`GUI did-fail-load: ${code} ${desc} @ ${theUrl}`);
    dialog.showErrorBox('GUI-Fehler', `Konnte GUI nicht laden:\n${desc} (Code ${code})`);
  });

  const showWindow = () => {
    if (!mainWindow) return;
    log.info('GUI did-finish-load');
    try { mainWindow.show(); } catch {}
    if (isDev) mainWindow.webContents.openDevTools();
  };
  mainWindow.webContents.once('did-finish-load', showWindow);
  mainWindow.once('ready-to-show', showWindow);

  mainWindow.on('closed', () => { mainWindow = null; });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url); return { action: 'deny' };
  });

  createMenu();
}

// ---- Tray -------------------------------------------------------------------
function createTray() {
  let trayImg = nativeImage.createFromPath(path.join(projectRoot, 'gui', 'icons', 'icon.png'));
  if (!trayImg || (trayImg.isEmpty && trayImg.isEmpty())) trayImg = nativeImage.createEmpty();
  tray = new Tray(trayImg.resize({ width: 16, height: 16 }));
  const menu = Menu.buildFromTemplate([
    { label: 'KI-Sprachassistent', enabled: false },
    { type: 'separator' },
    { label: 'Öffnen',     click: () => { if (mainWindow) { mainWindow.show(); mainWindow.focus(); } } },
    { label: 'Minimieren', click: () => { if (mainWindow) mainWindow.hide(); } },
    { type: 'separator' },
    { label: 'Beenden',    click: () => { app.isQuiting = true; app.quit(); } }
  ]);
  tray.setContextMenu(menu);
  tray.setToolTip('KI-Sprachassistent');
  tray.on('click', () => {
    if (!mainWindow) return;
    if (mainWindow.isVisible()) mainWindow.hide(); else { mainWindow.show(); mainWindow.focus(); }
  });
}

// ---- Backend ----------------------------------------------------------------
async function startBackend() {
  try {
    const backend = resolveBackendBinary();

    const env = { ...process.env };
    // einige generische Ports neutralisieren, damit Backend seine konfigurierten Ports nutzt
    delete env.PORT; delete env.HTTP_PORT; delete env.APP_PORT; delete env.NEXT_PUBLIC_PORT;

    console.log('[desktop] Spawning backend (%s): %s %s',
      app.isPackaged ? 'prod' : 'dev', backend.cmd, backend.args.join(' '));

    backendProcess = spawn(backend.cmd, backend.args, {
      env,
      cwd: projectRoot,
      stdio: 'inherit'
    });

    backendProcess.on('exit', (code) => console.log('[desktop] Backend exited', code));
    backendProcess.on('error', (err) => {
      log.error('Backend spawn error:', err);
      dialog.showMessageBox({
        type: 'error',
        title: 'Backend-Start fehlgeschlagen',
        message: err.message || String(err),
        buttons: ['OK', 'Build-Anleitung öffnen']
      }).then(result => {
        if (result.response === 1) {
          const doc = path.join(projectRoot, 'docs', 'Build-Anleitung.md');
          shell.openPath(doc).catch(() => {});
        }
      });
    });

    await waitForHealth();
  } catch (err) {
    log.error('Failed to start backend:', err);
    const res = await dialog.showMessageBox({
      type: 'error',
      title: 'Backend nicht erreichbar',
      message: err.message || String(err),
      buttons: ['Erneut versuchen', 'Beenden']
    });
    if (res.response === 0) {
      return startBackend();
    }
    throw err;
  }
}

function stopBackend() {
  if (backendProcess) {
    try { backendProcess.kill(); } catch {}
    backendProcess = null;
  }
}

// ---- Menu -------------------------------------------------------------------
function createMenu() {
  const template = [
    { label: 'Datei', submenu: [ { role: 'quit', label: 'Beenden' } ] },
    {
      label: 'Ansicht',
      submenu: [
        { role: 'reload', label: 'Neu laden' },
        { role: 'toggleDevTools', label: 'Entwicklertools' },
        { type: 'separator' },
        { role: 'resetZoom', label: 'Zoom zurücksetzen' },
        { role: 'zoomIn', label: 'Vergrößern' },
        { role: 'zoomOut', label: 'Verkleinern' },
        { type: 'separator' },
        { role: 'togglefullscreen', label: 'Vollbild' }
      ]
    }
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ---- IPC: TTS Plan (writes .env and relaunches app) -------------------------
function upsertEnvLine(envPath, key, val) {
  let content = '';
  try { content = fs.readFileSync(envPath, 'utf8'); } catch {}
  const re = new RegExp(`^${key}=.*$`, 'm');
  if (content.match(re)) content = content.replace(re, `${key}=${val}`);
  else content = (content ? content.replace(/\n*$/, '\n') : '') + `${key}=${val}\n`;
  fs.writeFileSync(envPath, content, 'utf8');
}

if (!global.__ttsPlanHandlerInstalled) {
  global.__ttsPlanHandlerInstalled = true;

  ipcMain.handle('tts-plan:set', async (_evt, { intro, main }) => {
    try {
      const envPath = path.join(projectRoot, '.env');

      upsertEnvLine(envPath, 'STAGED_TTS_INTRO_ENGINE', intro || 'auto');
      upsertEnvLine(envPath, 'STAGED_TTS_MAIN_ENGINE',  main  || 'auto');

      // kleiner Delay, dann App-Neustart (Backend startet neu mit neuen ENV)
      setTimeout(() => { app.relaunch(); app.exit(0); }, 150);

      return { ok: true, envPath };
    } catch (e) {
      return { ok: false, error: String(e) };
    }
  });
}

