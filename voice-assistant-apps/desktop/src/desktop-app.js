// Desktop-spezifische Erweiterungen für Electron
class DesktopVoiceAssistant {
  constructor() {
    this.isElectron = window.electronAPI?.isElectron || false;
    this.shortcuts = {};
    this.nativeNotifications = true;
    
    if (this.isElectron) {
      this.initializeDesktopFeatures();
      this.setupElectronEventListeners();
    }
  }

  initializeDesktopFeatures() {
    console.log('🖥️ Initializing Desktop Features');
    
    // Desktop-spezifische UI-Anpassungen
    this.adaptUIForDesktop();
    
    // Native Menü-Integration
    this.setupMenuIntegration();
    
    // Keyboard Shortcuts erweitern
    this.setupDesktopShortcuts();
    
    // Window-Management
    this.setupWindowManagement();
    
    // Native Notifications verwenden
    this.enableNativeNotifications();
    
    // Auto-Save für Einstellungen
    this.enableSettingsAutoSave();
    
    console.log('✅ Desktop Features initialisiert');
  }

  adaptUIForDesktop() {
    // Desktop-spezifische CSS-Klasse hinzufügen
    document.body.classList.add('desktop-app');
    
    // Titlebar anzeigen wenn frameless
    if (window.electronAPI?.platform !== 'darwin') {
      const titlebar = document.getElementById('customTitlebar');
      if (titlebar) {
        titlebar.style.display = 'block';
        document.body.style.paddingTop = '30px';
      }
    }
    
    // Rechtsklick-Kontextmenü erweitern
    this.setupContextMenu();
    
    // Drag & Drop Support
    this.enableDragDrop();
  }

  setupElectronEventListeners() {
    // Main Process Events
    window.electronAPI?.onClearConversation(() => {
      clearResponse();
      showDesktopNotification('Gespräch gelöscht', 'Ein neues Gespräch wurde gestartet');
    });

    window.electronAPI?.onOpenSettings(() => {
      openSettingsModal();
    });

    window.electronAPI?.onStartRecording(() => {
      if (!window.isRecording) {
        toggleRecording();
      }
    });

    window.electronAPI?.onStopRecording(() => {
      if (window.isRecording) {
        stopRecording();
      }
    });

    window.electronAPI?.onOpenAudioSettings(() => {
      openSettingsTab('audio');
    });

    // Window Events
    window.addEventListener('beforeunload', (e) => {
      this.saveSettingsToElectron();
      if (window.isRecording) {
        e.preventDefault();
        e.returnValue = 'Aufnahme läuft noch. Wirklich beenden?';
      }
    });
  }

  setupMenuIntegration() {
    // Erweiterte Menü-Aktionen
    window.desktopMenuActions = {
      newConversation: () => {
        clearResponse();
        document.getElementById('textInput').value = '';
        showDesktopNotification('Neues Gespräch', 'Bereit für neue Eingaben');
      },
      
      exportConversation: async () => {
        const conversation = this.getConversationHistory();
        try {
          const result = await window.electronAPI?.showSaveDialog();
          if (result && !result.canceled) {
            await this.saveConversationToFile(result.filePath, conversation);
            showDesktopNotification('Export erfolgreich', `Gespräch gespeichert: ${result.filePath}`);
          }
        } catch (error) {
          console.error('Export Fehler:', error);
          showDesktopNotification('Export fehlgeschlagen', error.message);
        }
      },
      
      toggleAlwaysOnTop: () => {
        // This would be handled in main process
        console.log('Toggle Always On Top');
      }
    };
  }

  setupDesktopShortcuts() {
    const shortcuts = {
      'ctrl+n': () => window.desktopMenuActions.newConversation(),
      'ctrl+s': () => window.desktopMenuActions.exportConversation(),
      'ctrl+,': () => openSettingsModal(),
      'f11': () => this.toggleFullscreen(),
      'ctrl+shift+i': () => this.toggleDevTools(),
      'ctrl+r': () => location.reload(),
      'alt+f4': () => window.close()
    };

    document.addEventListener('keydown', (e) => {
      const key = this.getShortcutKey(e);
      if (shortcuts[key]) {
        e.preventDefault();
        shortcuts[key]();
      }
    });

    this.shortcuts = shortcuts;
  }

  getShortcutKey(event) {
    const parts = [];
    if (event.ctrlKey) parts.push('ctrl');
    if (event.altKey) parts.push('alt');
    if (event.shiftKey) parts.push('shift');
    if (event.metaKey) parts.push('meta');
    
    const key = event.key.toLowerCase();
    if (key !== 'control' && key !== 'alt' && key !== 'shift' && key !== 'meta') {
      parts.push(key);
    }
    
    return parts.join('+');
  }

  setupWindowManagement() {
    // Zoom-Kontrolle
    let zoomLevel = 1.0;
    
    window.desktopZoom = {
      in: () => {
        zoomLevel = Math.min(zoomLevel + 0.1, 2.0);
        document.body.style.zoom = zoomLevel;
        showDesktopNotification('Zoom', `Vergrößert auf ${Math.round(zoomLevel * 100)}%`);
      },
      out: () => {
        zoomLevel = Math.max(zoomLevel - 0.1, 0.5);
        document.body.style.zoom = zoomLevel;
        showDesktopNotification('Zoom', `Verkleinert auf ${Math.round(zoomLevel * 100)}%`);
      },
      reset: () => {
        zoomLevel = 1.0;
        document.body.style.zoom = zoomLevel;
        showDesktopNotification('Zoom', 'Auf 100% zurückgesetzt');
      }
    };

    // Window State Management
    window.addEventListener('focus', () => {
      document.body.classList.add('window-focused');
    });

    window.addEventListener('blur', () => {
      document.body.classList.remove('window-focused');
    });
  }

  setupContextMenu() {
    document.addEventListener('contextmenu', (e) => {
      // Custom context menu für Desktop
      e.preventDefault();
      
      const contextMenu = document.createElement('div');
      contextMenu.className = 'desktop-context-menu';
      contextMenu.style.cssText = `
        position: fixed;
        top: ${e.clientY}px;
        left: ${e.clientX}px;
        background: var(--glass-bg);
        backdrop-filter: blur(20px);
        border: 1px solid var(--glass-border);
        border-radius: 8px;
        padding: 0.5rem;
        z-index: 10000;
        min-width: 150px;
      `;
      
      const menuItems = [
        { label: '🔄 Neu laden', action: () => location.reload() },
        { label: '📋 Kopieren', action: () => document.execCommand('copy') },
        { label: '📥 Einfügen', action: () => document.execCommand('paste') },
        { label: '⚙️ Einstellungen', action: () => openSettingsModal() },
        { label: '🔍 DevTools', action: () => this.toggleDevTools() }
      ];
      
      menuItems.forEach(item => {
        const menuItem = document.createElement('div');
        menuItem.textContent = item.label;
        menuItem.style.cssText = `
          padding: 0.5rem;
          cursor: pointer;
          border-radius: 4px;
          transition: background 0.2s ease;
        `;
        menuItem.addEventListener('click', () => {
          item.action();
          contextMenu.remove();
        });
        menuItem.addEventListener('mouseenter', () => {
          menuItem.style.background = 'rgba(255, 255, 255, 0.1)';
        });
        menuItem.addEventListener('mouseleave', () => {
          menuItem.style.background = 'transparent';
        });
        contextMenu.appendChild(menuItem);
      });
      
      document.body.appendChild(contextMenu);
      
      // Remove on click outside
      setTimeout(() => {
        document.addEventListener('click', () => contextMenu.remove(), { once: true });
      }, 100);
    });
  }

  enableDragDrop() {
    // Drag & Drop für Dateien
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
      document.addEventListener(eventName, this.handleDragDrop.bind(this), false);
    });
  }

  handleDragDrop(e) {
    e.preventDefault();
    e.stopPropagation();

    if (e.type === 'dragenter' || e.type === 'dragover') {
      document.body.classList.add('drag-over');
    } else if (e.type === 'dragleave') {
      document.body.classList.remove('drag-over');
    } else if (e.type === 'drop') {
      document.body.classList.remove('drag-over');
      
      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        this.handleDroppedFiles(files);
      }
    }
  }

  async handleDroppedFiles(files) {
    for (const file of files) {
      if (file.type.startsWith('text/') || file.name.endsWith('.json')) {
        try {
          const content = await this.readFileAsText(file);
          if (file.name.endsWith('.json')) {
            // Versuche Einstellungen zu importieren
            const settings = JSON.parse(content);
            if (this.validateSettings(settings)) {
              Object.assign(window.settings, settings);
              applySettings();
              showDesktopNotification('Einstellungen importiert', `Aus Datei: ${file.name}`);
            }
          } else {
            // Text in Eingabefeld einfügen
            document.getElementById('textInput').value = content.substring(0, 500);
            showDesktopNotification('Text eingefügt', `Aus Datei: ${file.name}`);
          }
        } catch (error) {
          showDesktopNotification('Fehler beim Lesen', `Datei: ${file.name}`);
        }
      } else if (file.type.startsWith('audio/')) {
        showDesktopNotification('Audio-Datei', 'Audio-Import wird in zukünftiger Version unterstützt');
      }
    }
  }

  readFileAsText(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsText(file);
    });
  }

  validateSettings(settings) {
    const requiredKeys = ['responseNebel', 'avatarAnimation', 'animationSpeed'];
    return requiredKeys.every(key => key in settings);
  }

  enableNativeNotifications() {
    // Desktop native notifications
    window.showDesktopNotification = (title, message, options = {}) => {
      if (this.nativeNotifications && window.electronAPI?.showNotification) {
        return window.electronAPI.showNotification(title, message, {
          icon: '../assets/icon.png',
          sound: true,
          ...options
        });
      } else {
        // Fallback zur Web GUI notification
        return showNotification('success', title, message);
      }
    };
  }

  enableSettingsAutoSave() {
    // Auto-save Einstellungen alle 30 Sekunden
    setInterval(() => {
      this.saveSettingsToElectron();
    }, 30000);

    // Save on settings change
    const originalApplySettings = window.applySettings;
    window.applySettings = () => {
      originalApplySettings?.();
      this.saveSettingsToElectron();
    };
  }

  saveSettingsToElectron() {
    if (window.electronAPI?.store && window.settings) {
      try {
        window.electronAPI.store.set('voice-assistant-settings', JSON.stringify(window.settings));
      } catch (error) {
        console.warn('Settings save error:', error);
      }
    }
  }

  loadSettingsFromElectron() {
    if (window.electronAPI?.store) {
      try {
        const savedSettings = window.electronAPI.store.get('voice-assistant-settings');
        if (savedSettings) {
          const parsed = JSON.parse(savedSettings);
          Object.assign(window.settings, parsed);
          applySettings();
          console.log('✅ Einstellungen aus Electron geladen');
        }
      } catch (error) {
        console.warn('Settings load error:', error);
      }
    }
  }

  getConversationHistory() {
    // Sammle Gesprächsverlauf aus der UI
    const messages = [];
    const responseElement = document.getElementById('response');
    
    if (responseElement && responseElement.textContent.trim() !== 'Ihre Antwort erscheint hier...') {
      messages.push({
        timestamp: new Date().toISOString(),
        type: 'response',
        content: responseElement.textContent
      });
    }
    
    return {
      version: '2.1.0',
      created: new Date().toISOString(),
      messages: messages,
      settings: window.settings
    };
  }

  async saveConversationToFile(filePath, conversation) {
    if (window.electronAPI?.writeFile) {
      await window.electronAPI.writeFile(filePath, JSON.stringify(conversation, null, 2));
    }
  }

  toggleFullscreen() {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      document.documentElement.requestFullscreen();
    }
  }

  toggleDevTools() {
    if (window.electronAPI?.toggleDevTools) {
      window.electronAPI.toggleDevTools();
    }
  }

  // System Information für Desktop
  async getDesktopSystemInfo() {
    const baseInfo = window.desktopAPI?.getSystemInfo() || {};
    const appVersion = await window.electronAPI?.getAppVersion() || '2.1.0';
    
    return {
      ...baseInfo,
      appVersion,
      memoryUsage: performance.memory ? {
        used: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024) + ' MB',
        total: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024) + ' MB',
        limit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024) + ' MB'
      } : 'Nicht verfügbar',
      screen: {
        width: screen.width,
        height: screen.height,
        colorDepth: screen.colorDepth
      },
      languages: navigator.languages.join(', '),
      online: navigator.onLine
    };
  }
}

// Desktop-spezifische CSS Styles hinzufügen
const desktopCSS = `
.desktop-app .drag-over {
  background: rgba(99, 102, 241, 0.1);
  border: 2px dashed var(--primary-color);
}

.desktop-app .window-focused {
  /* Styles für fokussiertes Fenster */
}

.desktop-context-menu {
  animation: contextMenuSlide 0.2s ease-out;
}

@keyframes contextMenuSlide {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.desktop-app .notification-container {
  /* Desktop notifications positioning */
  top: 80px;
  right: 20px;
}

.desktop-app .main-card {
  /* Enhanced desktop styling */
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

/* Scrollbar styling for desktop */
.desktop-app ::-webkit-scrollbar {
  width: 8px;
}

.desktop-app ::-webkit-scrollbar-track {
  background: var(--glass-bg);
  border-radius: 4px;
}

.desktop-app ::-webkit-scrollbar-thumb {
  background: var(--glass-border);
  border-radius: 4px;
}

.desktop-app ::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}
`;

// CSS zum Document hinzufügen
const desktopStyleSheet = document.createElement('style');
desktopStyleSheet.textContent = desktopCSS;
document.head.appendChild(desktopStyleSheet);

// Desktop App initialisieren
document.addEventListener('DOMContentLoaded', () => {
  window.desktopApp = new DesktopVoiceAssistant();
  
  // Lade Einstellungen nach normaler Initialisierung
  setTimeout(() => {
    if (window.desktopApp.isElectron) {
      window.desktopApp.loadSettingsFromElectron();
    }
  }, 1000);
});

// Erweiterte showSystemInfo für Desktop
if (typeof showSystemInfo !== 'undefined') {
  const originalShowSystemInfo = showSystemInfo;
  showSystemInfo = async () => {
    if (window.desktopApp?.isElectron) {
      const info = await window.desktopApp.getDesktopSystemInfo();
      let infoText = `Version: ${info.appVersion}\n`;
      infoText += `Plattform: ${info.platform}\n`;
      infoText += `Architektur: ${info.arch}\n`;
      infoText += `Electron: ${info.electronVersion}\n`;
      infoText += `Chrome: ${info.chromeVersion}\n`;
      infoText += `Node.js: ${info.nodeVersion}\n`;
      infoText += `Speicher: ${info.memoryUsage.used || 'N/A'}\n`;
      infoText += `Bildschirm: ${info.screen.width}x${info.screen.height}\n`;
      infoText += `Online: ${info.online ? 'Ja' : 'Nein'}`;
      
      showNotification('success', '📊 Desktop System-Information', infoText, 10000);
    } else {
      originalShowSystemInfo();
    }
  };
}

console.log('🖥️ Desktop App Extensions geladen');
