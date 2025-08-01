// Mobile-spezifische Anpassungen für Cordova
class MobileVoiceAssistant {
  constructor() {
    this.isReady = false;
    this.plugins = {};
    this.permissions = {};
    
    // Event Listener für Cordova
    if (typeof cordova !== 'undefined') {
      document.addEventListener('deviceready', this.onDeviceReady.bind(this), false);
      document.addEventListener('pause', this.onPause.bind(this), false);
      document.addEventListener('resume', this.onResume.bind(this), false);
      document.addEventListener('backbutton', this.onBackButton.bind(this), false);
    } else {
      // Fallback für Entwicklung ohne Cordova
      setTimeout(() => this.onDeviceReady(), 100);
    }
  }

  async onDeviceReady() {
    console.log('📱 Cordova Device Ready');
    this.isReady = true;
    
    // Plugins initialisieren
    await this.initializePlugins();
    
    // Berechtigungen anfordern
    await this.requestPermissions();
    
    // Mobile UI anpassen
    this.adaptUIForMobile();
    
    // Status Bar konfigurieren
    this.configureStatusBar();
    
    // Splash Screen ausblenden
    if (navigator.splashscreen) {
      setTimeout(() => {
        navigator.splashscreen.hide();
      }, 1000);
    }
    
    // App-spezifische Initialisierung
    this.initializeMobileFeatures();
    
    console.log('✅ Mobile App vollständig initialisiert');
  }

  async initializePlugins() {
    // Verfügbare Plugins testen
    this.plugins = {
      device: window.device || null,
      network: navigator.connection || null,
      vibration: navigator.vibrate || null,
      media: window.Media || null,
      file: window.resolveLocalFileSystemURL || null,
      speech: window.plugins?.speechRecognition || null,
      tts: window.plugins?.tts || null,
      localNotification: window.plugin?.notification?.local || null,
      backgroundMode: window.plugin?.backgroundMode || null
    };

    console.log('📦 Verfügbare Plugins:', Object.keys(this.plugins).filter(key => this.plugins[key]));
  }

  async requestPermissions() {
    if (!window.cordova?.plugins?.diagnostic) return;

    const permissions = [
      'RECORD_AUDIO',
      'MODIFY_AUDIO_SETTINGS',
      'WRITE_EXTERNAL_STORAGE',
      'READ_EXTERNAL_STORAGE'
    ];

    for (const permission of permissions) {
      try {
        const status = await this.checkPermission(permission);
        if (status !== 'GRANTED') {
          await this.requestPermission(permission);
        }
        this.permissions[permission] = status;
      } catch (error) {
        console.warn(`⚠️ Berechtigung ${permission} konnte nicht angefordert werden:`, error);
      }
    }
  }

  checkPermission(permission) {
    return new Promise((resolve) => {
      if (window.cordova?.plugins?.permissions) {
        window.cordova.plugins.permissions.checkPermission(
          `android.permission.${permission}`,
          (status) => resolve(status.hasPermission ? 'GRANTED' : 'DENIED'),
          (error) => resolve('ERROR')
        );
      } else {
        resolve('GRANTED'); // Fallback
      }
    });
  }

  requestPermission(permission) {
    return new Promise((resolve) => {
      if (window.cordova?.plugins?.permissions) {
        window.cordova.plugins.permissions.requestPermission(
          `android.permission.${permission}`,
          (status) => resolve(status.hasPermission ? 'GRANTED' : 'DENIED'),
          (error) => resolve('ERROR')
        );
      } else {
        resolve('GRANTED'); // Fallback
      }
    });
  }

  adaptUIForMobile() {
    // Viewport Meta-Tag für mobile Geräte
    const viewport = document.querySelector('meta[name="viewport"]');
    if (viewport) {
      viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover';
    }

    // Mobile CSS-Klasse hinzufügen
    document.body.classList.add('mobile-device');
    
    // Touch-Events für bessere Responsivität
    this.enableTouchOptimizations();
    
    // Scroll-Verhalten anpassen
    this.configureScrolling();
    
    // Mobile-spezifische Layout-Anpassungen
    this.adjustLayoutForMobile();
  }

  enableTouchOptimizations() {
    // Touch-Events für alle Buttons
    document.querySelectorAll('button, .btn, .settings-toggle, .color-option').forEach(element => {
      element.addEventListener('touchstart', (e) => {
        element.classList.add('touch-active');
      });
      
      element.addEventListener('touchend', (e) => {
        setTimeout(() => element.classList.remove('touch-active'), 150);
      });
    });

    // Haptic Feedback
    if (this.plugins.vibration) {
      document.querySelectorAll('button, .btn').forEach(button => {
        button.addEventListener('click', () => {
          navigator.vibrate(50); // Kurze Vibration
        });
      });
    }
  }

  configureScrolling() {
    // iOS-Style Scroll-Bounce deaktivieren
    document.addEventListener('touchmove', (e) => {
      if (e.target.closest('.scrollable')) return;
      e.preventDefault();
    }, { passive: false });

    // Pull-to-refresh deaktivieren
    document.body.style.overscrollBehavior = 'none';
  }

  adjustLayoutForMobile() {
    // Container-Größe für mobile Geräte anpassen
    const container = document.querySelector('.container');
    if (container) {
      container.style.padding = '1rem';
      container.style.maxWidth = '100%';
    }

    // Settings-Modal für mobile Geräte anpassen
    const settingsModal = document.getElementById('settingsModal');
    if (settingsModal) {
      settingsModal.classList.add('mobile-modal');
    }

    // Avatar-Größe für mobile Geräte reduzieren
    const avatar = document.querySelector('.avatar');
    if (avatar) {
      avatar.style.width = '80px';
      avatar.style.height = '80px';
    }
  }

  configureStatusBar() {
    if (window.StatusBar) {
      // StatusBar-Stil setzen
      StatusBar.styleDefault();
      StatusBar.backgroundColorByHexString('#0f0f23');
      
      // StatusBar anzeigen
      StatusBar.show();
      
      // Overlay-Modus deaktivieren
      if (StatusBar.overlaysWebView) {
        StatusBar.overlaysWebView(false);
      }
    }
  }

  initializeMobileFeatures() {
    // Mobile Spracherkennung initialisieren
    this.initializeMobileSpeechRecognition();
    
    // Mobile Text-to-Speech initialisieren
    this.initializeMobileTTS();
    
    // Background-Mode konfigurieren
    this.configureBackgroundMode();
    
    // Lokale Benachrichtigungen initialisieren
    this.initializeLocalNotifications();
    
    // Network-Status überwachen
    this.monitorNetworkStatus();
  }

  initializeMobileSpeechRecognition() {
    if (!this.plugins.speech) return;

    // Mobile Spracherkennung konfigurieren
    window.mobileSpeechRecognition = {
      start: () => {
        return new Promise((resolve, reject) => {
          window.plugins.speechRecognition.startListening((result) => {
            resolve(result[0] || '');
          }, (error) => {
            reject(error);
          }, {
            language: 'de-DE',
            matches: 1,
            prompt: 'Sprechen Sie jetzt...',
            showPopup: false
          });
        });
      },
      
      stop: () => {
        if (window.plugins.speechRecognition.stopListening) {
          window.plugins.speechRecognition.stopListening();
        }
      }
    };
  }

  initializeMobileTTS() {
    if (!this.plugins.tts) return;

    window.mobileTTS = {
      speak: (text, options = {}) => {
        return new Promise((resolve, reject) => {
          window.plugins.tts.speak({
            text: text,
            locale: options.lang || 'de-DE',
            rate: options.rate || 1.0,
            pitch: options.pitch || 1.0
          }, resolve, reject);
        });
      },
      
      stop: () => {
        if (window.plugins.tts.stop) {
          window.plugins.tts.stop();
        }
      }
    };
  }

  configureBackgroundMode() {
    if (!this.plugins.backgroundMode) return;

    // Background-Mode konfigurieren
    cordova.plugins.backgroundMode.setDefaults({
      title: 'KI-Sprachassistent',
      text: 'App läuft im Hintergrund',
      icon: 'icon',
      color: '6366f1',
      resume: true,
      hidden: false,
      bigText: false
    });

    // Background-Mode aktivieren wenn nötig
    cordova.plugins.backgroundMode.enable();
  }

  initializeLocalNotifications() {
    if (!this.plugins.localNotification) return;

    // Berechtigung für Benachrichtigungen anfordern
    cordova.plugins.notification.local.requestPermission((granted) => {
      console.log('📢 Notification permission:', granted);
    });

    window.mobileNotifications = {
      show: (title, message, options = {}) => {
        cordova.plugins.notification.local.schedule({
          id: Date.now(),
          title: title,
          text: message,
          sound: options.sound !== false,
          vibrate: options.vibrate !== false,
          led: { color: '#6366f1', on: 1000, off: 1000 },
          ...options
        });
      }
    };
  }

  monitorNetworkStatus() {
    if (!this.plugins.network) return;

    const updateNetworkStatus = () => {
      const networkState = navigator.connection.type;
      const states = {};
      states[Connection.UNKNOWN] = 'Unbekannt';
      states[Connection.ETHERNET] = 'Ethernet';
      states[Connection.WIFI] = 'WiFi';
      states[Connection.CELL_2G] = '2G';
      states[Connection.CELL_3G] = '3G';
      states[Connection.CELL_4G] = '4G';
      states[Connection.CELL] = 'Mobil';
      states[Connection.NONE] = 'Offline';

      const statusText = states[networkState] || 'Unbekannt';
      console.log('📶 Netzwerk-Status:', statusText);
      
      // UI-Update für Netzwerk-Status
      const isOnline = networkState !== Connection.NONE;
      document.body.classList.toggle('offline', !isOnline);
      
      if (!isOnline && window.settings?.notifications) {
        showNotification('warning', 'Offline', 'Keine Internetverbindung verfügbar');
      }
    };

    document.addEventListener('online', updateNetworkStatus, false);
    document.addEventListener('offline', updateNetworkStatus, false);
    updateNetworkStatus(); // Initial check
  }

  onPause() {
    console.log('📱 App pausiert');
    // Aufnahme stoppen wenn aktiv
    if (window.isRecording) {
      stopRecording();
    }
  }

  onResume() {
    console.log('📱 App fortgesetzt');
    // WebSocket-Verbindung prüfen
    if (window.ws && window.ws.readyState !== WebSocket.OPEN) {
      initWebSocket();
    }
  }

  onBackButton(e) {
    e.preventDefault();
    
    // Settings-Modal schließen wenn offen
    const settingsModal = document.getElementById('settingsModal');
    if (settingsModal?.classList.contains('active')) {
      closeSettingsModal();
      return;
    }
    
    // Settings-Menu schließen wenn offen
    const settingsMenu = document.getElementById('settingsMenu');
    if (settingsMenu?.classList.contains('active')) {
      settingsMenu.classList.remove('active');
      return;
    }
    
    // Aufnahme stoppen wenn aktiv
    if (window.isRecording) {
      stopRecording();
      return;
    }
    
    // App minimieren statt beenden
    if (navigator.app?.exitApp) {
      navigator.app.exitApp();
    }
  }

  // Utility-Methoden für mobile Features
  static isMobile() {
    return typeof cordova !== 'undefined' || /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  }

  static getDeviceInfo() {
    if (window.device) {
      return {
        platform: device.platform,
        version: device.version,
        model: device.model,
        manufacturer: device.manufacturer || 'Unknown',
        uuid: device.uuid,
        cordova: device.cordova
      };
    }
    return null;
  }

  static vibrate(pattern = 100) {
    if (navigator.vibrate) {
      navigator.vibrate(pattern);
    }
  }
}

// Mobile CSS Anpassungen hinzufügen
const mobileCSS = `
.mobile-device {
  -webkit-user-select: none;
  user-select: none;
  -webkit-touch-callout: none;
  -webkit-tap-highlight-color: rgba(0,0,0,0);
}

.mobile-device .container {
  padding: env(safe-area-inset-top) 1rem env(safe-area-inset-bottom) 1rem;
  min-height: 100vh;
  min-height: -webkit-fill-available;
}

.mobile-device .settings-header {
  padding-top: calc(env(safe-area-inset-top) + 1rem);
}

.mobile-device .touch-active {
  transform: scale(0.95);
  transition: transform 0.1s ease;
}

.mobile-device .avatar {
  width: 80px !important;
  height: 80px !important;
}

.mobile-device .main-card {
  margin: 0.5rem;
  padding: 1.5rem;
}

.mobile-device .settings-modal .settings-content {
  width: 95%;
  max-height: 90vh;
  margin: 5vh auto;
}

.mobile-device .notification-container {
  top: calc(env(safe-area-inset-top) + 80px);
  right: 10px;
  left: 10px;
  max-width: none;
}

.offline::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: #ef4444;
  z-index: 9999;
  animation: pulse 2s infinite;
}

@media (max-width: 480px) {
  .mobile-device .settings-tabs {
    flex-wrap: wrap;
    gap: 0.25rem;
  }
  
  .mobile-device .settings-tab {
    font-size: 0.8rem;
    padding: 0.5rem 0.75rem;
  }
  
  .mobile-device .input-section {
    flex-direction: column;
    gap: 0.75rem;
  }
}
`;

// CSS zum Document hinzufügen
const styleSheet = document.createElement('style');
styleSheet.textContent = mobileCSS;
document.head.appendChild(styleSheet);

// Mobile App initialisieren
const mobileApp = new MobileVoiceAssistant();

// Global verfügbar machen
window.mobileApp = mobileApp;
