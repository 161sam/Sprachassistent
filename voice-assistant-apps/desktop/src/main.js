const { app, BrowserWindow, Menu, dialog, shell, Tray, nativeImage } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const log = require('electron-log');
const { autoUpdater } = require('electron-updater');
const dotenv = require('dotenv');
const http = require('http');
const url = require('url');
const net = require('net');

const https = require('http');

async function waitForHealth(url='http://127.0.0.1:48232/health', retries=120, delay=500) {
  return new Promise((resolve, reject) => {
    const ping = () => {
      const req = https.get(url, res => {
        if (res.statusCode === 200) { res.resume(); resolve(); }
        else { res.resume(); retries-- > 0 ? setTimeout(ping, delay) : reject(new Error('health check failed')); }
      });
      req.on('error', () => { retries-- > 0 ? setTimeout(ping, delay) : reject(new Error('health check error')); });
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

function resolveBackendBinary(projectRoot) {
  const isDev = !app.isPackaged;
  if (isDev) {
    // Prefer explicit PYTHON env but fall back to platform defaults.
    // On Linux/macOS use `python3` to avoid missing `python` shim.
    // On Windows keep `python` as the typical command.
    const pythonCmd = process.env.PYTHON
      || (process.platform === 'win32' ? 'python' : 'python3');
    return {
      cmd: pythonCmd,
      args: [path.join(projectRoot, 'backend', 'ws-server', 'ws-server.py')],
      mode: 'script'
    };
  }
  const base = process.resourcesPath;
  const bin = process.platform === 'win32'
    ? path.join(base, 'bin', 'win', 'ws-server.exe')
    : path.join(base, 'bin', 'linux', 'ws-server');
  return { cmd: bin, args: [], mode: 'binary' };
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
  const rootEnv = path.join(projectRoot, '.env');
  const localEnv = path.join(__dirname, '../.env');
  const envPath = fs.existsSync(rootEnv) ? rootEnv : localEnv;
  const defaultsPath = path.join(path.dirname(envPath), '.env.defaults');
  if (fs.existsSync(defaultsPath)) dotenv.config({ path: defaultsPath });
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

  guiServer = http.createServer((req,res)=>{
    try {
      let reqPath = decodeURIComponent((url.parse(req.url).pathname) || '/');
      if (reqPath === '/') reqPath = '/index.html';
      let filePath = path.join(guiRoot, safe(reqPath));
      if (!fs.existsSync(filePath) && reqPath.startsWith('/voice-assistant-apps/shared/')) {
        filePath = path.join(shared, safe(reqPath.replace(/^\/voice-assistant-apps\/shared\//,'')));
      }
      if (!fs.existsSync(filePath)) { res.statusCode=404; return res.end('Not Found'); }
      res.setHeader('Content-Type', mime[path.extname(filePath)] || 'application/octet-stream');
      fs.createReadStream(filePath).pipe(res);
    } catch(e) { res.statusCode=500; res.end('Server error'); }
  }).listen(guiPort, '127.0.0.1', ()=> log.info(`GUI static server: http://127.0.0.1:${guiPort}`));
  guiServer.on('error', e => log.error('GUI server error', e));
}

// ---- Main Window ------------------------------------------------------------
function createMainWindow() {
  // Icon: nimm deine vorhandenen Dateien
  let iconPath = path.join(projectRoot,'gui','icons','icon-512x512.png');
  if (!fs.existsSync(iconPath)) iconPath = path.join(projectRoot,'gui','icons','icon.png');

  const preload = path.join(__dirname, 'preload.js');
  const hasPreload = fs.existsSync(preload);

  mainWindow = new BrowserWindow({
    width: 1200, height: 900, minWidth: 800, minHeight: 600,
    show: false, backgroundColor: '#0f0f23',
    icon: fs.existsSync(iconPath) ? iconPath : undefined,
    titleBarStyle: isMac ? 'hiddenInset' : 'default',
    webPreferences: {
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
  mainWindow.webContents.on('did-finish-load', () => log.info('GUI did-finish-load'));

  mainWindow.once('ready-to-show', () => {
    try { mainWindow.show(); } catch {}
    if (isDev) mainWindow.webContents.openDevTools();
  });

  mainWindow.on('closed', () => { mainWindow = null; });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url); return { action: 'deny' };
  });

  createMenu();
}

// ---- Tray -------------------------------------------------------------------
function createTray() {
  let trayImg = nativeImage.createFromPath(path.join(projectRoot,'gui','icons','icon.png'));
  if (!trayImg || (trayImg.isEmpty && trayImg.isEmpty())) trayImg = nativeImage.createEmpty();
  tray = new Tray(trayImg.resize({ width: 16, height: 16 }));
  const menu = Menu.buildFromTemplate([
    { label:'KI-Sprachassistent', enabled:false },
    { type:'separator' },
    { label:'Öffnen', click:()=>{ if (mainWindow){ mainWindow.show(); mainWindow.focus(); } } },
    { label:'Minimieren', click:()=>{ if (mainWindow) mainWindow.hide(); } },
    { type:'separator' },
    { label:'Beenden', click:()=>{ app.isQuiting=true; app.quit(); } }
  ]);
  tray.setContextMenu(menu);
  tray.setToolTip('KI-Sprachassistent');
  tray.on('click', () => {
    if (!mainWindow) return;
    if (mainWindow.isVisible()) mainWindow.hide(); else { mainWindow.show(); mainWindow.focus(); }
  });
}

// ---- Backend ----------------------------------------------------------------
function waitForPort(port, host = '127.0.0.1', retries = 240, delay = 500) {
  return new Promise((resolve, reject) => {
    const tryConnect = () => {
      const socket = net.connect(port, host, () => {
        socket.end();
        resolve();
      });
      socket.on('error', () => {
        socket.destroy();
        if (retries-- <= 0) {
          reject(new Error('Backend start timed out'));
        } else {
          setTimeout(tryConnect, delay);
        }
      });
    };
    tryConnect();
  });
}

async function startBackend() {
  try {
    const backend = resolveBackendBinary(projectRoot);

    // --- FORCE LOCAL WS ENV (autopatch) ---
    const env = {
      ...process.env,
      WS_HOST: '127.0.0.1',
      WS_PORT: '48231',
      METRICS_PORT: '48232',
      JWT_SECRET: process.env.JWT_SECRET || 'devsecret',
      JWT_ALLOW_PLAIN: process.env.JWT_ALLOW_PLAIN || '1',
      JWT_BYPASS: process.env.JWT_BYPASS || '0'
    };
    delete env.PORT; delete env.HTTP_PORT; delete env.APP_PORT; delete env.NEXT_PUBLIC_PORT;

    console.log('[desktop] Spawning backend (%s): %s %s', app.isPackaged ? 'prod' : 'dev', backend.cmd, backend.args.join(' '));

    backendProcess = spawn(backend.cmd, backend.args, {
      env,
      cwd: projectRoot,
      stdio: 'inherit'
    });
    backendProcess.on('exit', (code) => console.log('[desktop] Backend exited', code));
    // Handle spawn errors (e.g. missing Python binary) to avoid crashing
    backendProcess.on('error', (err) => {
      log.error('Backend spawn error:', err);
      dialog.showErrorBox('Backend-Start fehlgeschlagen', err.message || String(err));
    });

    await waitForHealth();
  } catch (err) {
    log.error('Failed to start backend:', err);
    dialog.showErrorBox('Backend-Start fehlgeschlagen', err.message || String(err));
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
    { label: 'Datei', submenu: [ { role:'quit', label:'Beenden' } ] },
    {
      label: 'Ansicht',
      submenu: [
        { role: 'reload', label: 'Neu laden' },
        { role: 'toggleDevTools', label: 'Entwicklertools' },
        { type:'separator' },
        { role: 'resetZoom', label: 'Zoom zurücksetzen' },
        { role: 'zoomIn', label: 'Vergrößern' },
        { role: 'zoomOut', label: 'Verkleinern' },
        { type:'separator' },
        { role: 'togglefullscreen', label: 'Vollbild' }
      ]
    }
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}
