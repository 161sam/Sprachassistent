const { app, BrowserWindow, Menu, ipcMain, dialog, shell, Tray, nativeImage } = require('electron');
const path = require('path');
const log = require('electron-log');
const { autoUpdater } = require('electron-updater');

// Konfiguration
const isDev = process.env.NODE_ENV === 'development' || process.argv.includes('--dev');
const isWindows = process.platform === 'win32';
const isMac = process.platform === 'darwin';

let mainWindow;
let tray;

// Logging konfigurieren
log.transports.file.level = 'info';
autoUpdater.logger = log;

// Single Instance Lock
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}

// App Event Handlers
app.whenReady().then(() => {
  createMainWindow();
  createTray();
  createMenu();
  
  if (!isDev) {
    autoUpdater.checkForUpdatesAndNotify();
  }
});

app.on('window-all-closed', () => {
  if (!isMac) {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createMainWindow();
  }
});

// Hauptfenster erstellen
function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js')
    },
    titleBarStyle: isMac ? 'hiddenInset' : 'default',
    show: false,
    backgroundColor: '#0f0f23',
    icon: path.join(__dirname, '../assets/icon.png')
  });

  // HTML laden
  mainWindow.loadFile(path.join(__dirname, 'index.html'));

  // DevTools in Development
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  // Fenster anzeigen wenn bereit
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    
    if (isDev) {
      mainWindow.webContents.openDevTools();
    }
  });

  // Fenster Events
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  mainWindow.on('minimize', (event) => {
    if (isWindows) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('close', (event) => {
    if (!app.isQuiting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  // External Links in Browser öffnen
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

// System Tray erstellen
function createTray() {
  const trayIcon = nativeImage.createFromPath(path.join(__dirname, '../assets/tray-icon.png'));
  tray = new Tray(trayIcon.resize({ width: 16, height: 16 }));
  
  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'KI-Sprachassistent',
      type: 'normal',
      enabled: false
    },
    { type: 'separator' },
    {
      label: 'Öffnen',
      click: () => {
        mainWindow.show();
        mainWindow.focus();
      }
    },
    {
      label: 'Minimieren',
      click: () => {
        mainWindow.hide();
      }
    },
    { type: 'separator' },
    {
      label: 'Beenden',
      click: () => {
        app.isQuiting = true;
        app.quit();
      }
    }
  ]);

  tray.setContextMenu(contextMenu);
  tray.setToolTip('KI-Sprachassistent');
  
  tray.on('click', () => {
    if (mainWindow.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

// Anwendungsmenü erstellen
function createMenu() {
  const template = [
    {
      label: 'Datei',
      submenu: [
        {
          label: 'Neues Gespräch',
          accelerator: 'CmdOrCtrl+N',
          click: () => {
            mainWindow.webContents.send('clear-conversation');
          }
        },
        { type: 'separator' },
        {
          label: 'Einstellungen',
          accelerator: 'CmdOrCtrl+,',
          click: () => {
            mainWindow.webContents.send('open-settings');
          }
        },
        { type: 'separator' },
        {
          label: isMac ? 'Beenden' : 'Beenden',
          accelerator: isMac ? 'Cmd+Q' : 'Ctrl+Q',
          click: () => {
            app.isQuiting = true;
            app.quit();
          }
        }
      ]
    },
    {
      label: 'Bearbeiten',
      submenu: [
        { role: 'undo', label: 'Rückgängig' },
        { role: 'redo', label: 'Wiederholen' },
        { type: 'separator' },
        { role: 'cut', label: 'Ausschneiden' },
        { role: 'copy', label: 'Kopieren' },
        { role: 'paste', label: 'Einfügen' },
        { role: 'selectall', label: 'Alles auswählen' }
      ]
    },
    {
      label: 'Ansicht',
      submenu: [
        { role: 'reload', label: 'Neu laden' },
        { role: 'forceReload', label: 'Erzwingen neu laden' },
        { role: 'toggleDevTools', label: 'Entwicklertools' },
        { type: 'separator' },
        { role: 'resetZoom', label: 'Zoom zurücksetzen' },
        { role: 'zoomIn', label: 'Vergrößern' },
        { role: 'zoomOut', label: 'Verkleinern' },
        { type: 'separator' },
        { role: 'togglefullscreen', label: 'Vollbild' }
      ]
    },
    {
      label: 'Audio',
      submenu: [
        {
          label: 'Spracheingabe starten',
          accelerator: 'CmdOrCtrl+Enter',
          click: () => {
            mainWindow.webContents.send('start-recording');
          }
        },
        {
          label: 'Aufnahme stoppen',
          accelerator: 'Escape',
          click: () => {
            mainWindow.webContents.send('stop-recording');
          }
        },
        { type: 'separator' },
        {
          label: 'Audio-Einstellungen',
          click: () => {
            mainWindow.webContents.send('open-audio-settings');
          }
        }
      ]
    },
    {
      label: 'Fenster',
      submenu: [
        { role: 'minimize', label: 'Minimieren' },
        { role: 'close', label: 'Schließen' },
        ...(isMac ? [
          { type: 'separator' },
          { role: 'front', label: 'Alle nach vorne' }
        ] : [])
      ]
    },
    {
      label: 'Hilfe',
      submenu: [
        {
          label: 'Über KI-Sprachassistent',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'Über KI-Sprachassistent',
              message: 'KI-Sprachassistent v2.1.0',
              detail: 'Ein intelligenter Sprachassistent für Desktop-Systeme.\n\nEntwickelt für Raspberry Pi und Desktop-Computer.\n\n© 2025 Voice Assistant Team'
            });
          }
        },
        {
          label: 'System-Information',
          click: () => {
            const info = {
              version: app.getVersion(),
              electron: process.versions.electron,
              node: process.versions.node,
              chrome: process.versions.chrome,
              platform: process.platform,
              arch: process.arch
            };
            
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'System-Information',
              message: 'System-Details',
              detail: `Version: ${info.version}\nElectron: ${info.electron}\nNode.js: ${info.node}\nChrome: ${info.chrome}\nPlattform: ${info.platform}\nArchitektur: ${info.arch}`
            });
          }
        },
        { type: 'separator' },
        {
          label: 'GitHub Repository',
          click: () => {
            shell.openExternal('https://github.com/your-repo/ki-sprachassistent');
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// IPC Handlers
ipcMain.handle('get-app-version', () => {
  return app.getVersion();
});

ipcMain.handle('show-error-dialog', async (event, title, message) => {
  const result = await dialog.showMessageBox(mainWindow, {
    type: 'error',
    title: title,
    message: message,
    buttons: ['OK']
  });
  return result;
});

ipcMain.handle('show-save-dialog', async () => {
  const result = await dialog.showSaveDialog(mainWindow, {
    filters: [
      { name: 'JSON Files', extensions: ['json'] },
      { name: 'Text Files', extensions: ['txt'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  });
  return result;
});

// Auto Updater Events
autoUpdater.on('checking-for-update', () => {
  log.info('Checking for update...');
});

autoUpdater.on('update-available', (info) => {
  log.info('Update available.');
  dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: 'Update verfügbar',
    message: 'Eine neue Version ist verfügbar. Sie wird im Hintergrund heruntergeladen.',
    buttons: ['OK']
  });
});

autoUpdater.on('update-not-available', (info) => {
  log.info('Update not available.');
});

autoUpdater.on('error', (err) => {
  log.error('Error in auto-updater:', err);
});

autoUpdater.on('download-progress', (progressObj) => {
  let logMessage = `Download speed: ${progressObj.bytesPerSecond}`;
  logMessage += ` - Downloaded ${progressObj.percent}%`;
  logMessage += ` (${progressObj.transferred}/${progressObj.total})`;
  log.info(logMessage);
});

autoUpdater.on('update-downloaded', (info) => {
  log.info('Update downloaded');
  dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: 'Update bereit',
    message: 'Update wurde heruntergeladen. Die Anwendung wird beim nächsten Start aktualisiert.',
    buttons: ['Jetzt neustarten', 'Später']
  }).then((result) => {
    if (result.response === 0) {
      autoUpdater.quitAndInstall();
    }
  });
});
