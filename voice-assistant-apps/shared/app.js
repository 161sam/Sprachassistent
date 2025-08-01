// Gemeinsame Sprachassistent-Logik für Desktop und Mobile
// Kann sowohl in Electron als auch Cordova verwendet werden

class VoiceAssistantCore {
  constructor() {
    this.isInitialized = false;
    this.platform = this.detectPlatform();
    this.ws = null;
    this.isRecording = false;
    this.mediaRecorder = null;
    this.recordingTimer = null;
    this.recordingStartTime = null;
    
    // Settings mit Platform-Detection
    this.settings = {
      responseNebel: true,
      avatarAnimation: true,
      animationSpeed: 1.0,
      nebelColors: {
        primary: '#6366f1',
        secondary: '#10b981', 
        accent: '#f59e0b'
      },
      autoStopTime: 30000,
      noiseSuppression: true,
      echoCancellation: true,
      notifications: true,
      reducedMotion: false,
      glassOpacity: 0.05,
      autoReconnect: true,
      connectionTimeout: 3000,
      debugMode: false,
      // Platform-spezifische Settings
      platform: {
        mobile: {
          hapticFeedback: true,
          backgroundMode: false,
          touchOptimizations: true
        },
        desktop: {
          trayIcon: true,
          startMinimized: false,
          alwaysOnTop: false
        }
      }
    };

    console.log(`🚀 Voice Assistant Core initialisiert (Platform: ${this.platform})`);
  }

  detectPlatform() {
    // Cordova/Mobile Detection
    if (typeof cordova !== 'undefined') {
      return 'mobile';
    }
    
    // Electron/Desktop Detection
    if (typeof window !== 'undefined' && window.electronAPI?.isElectron) {
      return 'desktop';
    }
    
    // Web Browser Detection
    if (typeof window !== 'undefined') {
      const userAgent = navigator.userAgent.toLowerCase();
      if (/android|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent)) {
        return 'mobile-web';
      }
      return 'web';
    }
    
    return 'unknown';
  }

  async initialize() {
    if (this.isInitialized) return;

    console.log('🔧 Initialisiere Voice Assistant Core...');

    try {
      // Platform-spezifische Initialisierung
      await this.initializePlatformFeatures();
      
      // Gemeinsame Initialisierung
      this.initializeWebSocket();
      this.setupEventListeners();
      this.loadSettings();
      this.applySettings();
      
      this.isInitialized = true;
      console.log('✅ Voice Assistant Core erfolgreich initialisiert');
      
      // Notification über erfolgreiche Initialisierung
      this.showNotification('success', 'System bereit', 'Sprachassistent ist einsatzbereit');
      
    } catch (error) {
      console.error('❌ Fehler bei der Initialisierung:', error);
      this.showNotification('error', 'Initialisierungsfehler', error.message);
    }
  }

  async initializePlatformFeatures() {
    switch (this.platform) {
      case 'mobile':
        await this.initializeMobileFeatures();
        break;
      case 'desktop':
        await this.initializeDesktopFeatures();
        break;
      case 'mobile-web':
        await this.initializeMobileWebFeatures();
        break;
      case 'web':
        await this.initializeWebFeatures();
        break;
      default:
        console.warn('⚠️ Unbekannte Plattform, verwende Standard-Features');
    }
  }

  async initializeMobileFeatures() {
    console.log('📱 Initialisiere Mobile Features...');
    
    // Mobile App Class laden falls verfügbar
    if (typeof window !== 'undefined' && window.mobileApp) {
      await window.mobileApp.onDeviceReady();
    }
    
    // Mobile-spezifische Settings
    this.settings.autoStopTime = 15000; // Kürzere Aufnahmezeit auf Mobile
    this.settings.platform.mobile.hapticFeedback = true;
  }

  async initializeDesktopFeatures() {
    console.log('🖥️ Initialisiere Desktop Features...');
    
    // Desktop App Class laden falls verfügbar
    if (typeof window !== 'undefined' && window.desktopApp) {
      await window.desktopApp.initializeDesktopFeatures();
    }
    
    // Desktop-spezifische Settings
    this.settings.autoStopTime = 30000; // Längere Aufnahmezeit auf Desktop
    this.settings.platform.desktop.trayIcon = true;
  }

  async initializeMobileWebFeatures() {
    console.log('📱🌐 Initialisiere Mobile Web Features...');
    // PWA Features, Service Worker, etc.
    this.registerServiceWorker();
  }

  async initializeWebFeatures() {
    console.log('🌐 Initialisiere Web Features...');
    // Standard Web Features
    this.registerServiceWorker();
  }

  registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js')
        .then(registration => {
          console.log('🔄 Service Worker registriert:', registration);
        })
        .catch(error => {
          console.warn('⚠️ Service Worker Registrierung fehlgeschlagen:', error);
        });
    }
  }

  initializeWebSocket() {
    console.log('🔌 Initialisiere WebSocket-Verbindung...');
    
    try {
      // Flexible WebSocket URL basierend auf Umgebung
      const wsUrl = this.getWebSocketURL();
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        this.updateStatus('connected', '✅ Verbunden mit Sprachassistent');
        this.showNotification('success', 'Verbunden', 'Erfolgreich mit dem Sprachassistenten verbunden');
      };
      
      this.ws.onmessage = (event) => {
        this.hideNebelAnimation();
        try {
          const data = JSON.parse(event.data);
          this.displayResponse(data.content || event.data);
        } catch (e) {
          this.displayResponse(event.data);
        }
      };
      
      this.ws.onclose = () => {
        this.updateStatus('error', '❌ Verbindung getrennt');
        this.showNotification('error', 'Verbindung getrennt', 'Versuche automatisch zu reconnecten...');
        
        if (this.settings.autoReconnect) {
          setTimeout(() => this.initializeWebSocket(), this.settings.connectionTimeout);
        }
      };
      
      this.ws.onerror = (err) => {
        this.updateStatus('error', '❌ Verbindungsfehler');
        this.showNotification('error', 'Server nicht erreichbar', 'Bitte überprüfen Sie die Serververbindung');
        
        if (this.settings.debugMode) {
          console.error('WebSocket Error:', err);
        }
      };
      
    } catch (e) {
      this.updateStatus('error', '❌ Server nicht erreichbar');
      this.showNotification('error', 'Server nicht erreichbar', 'Bitte überprüfen Sie die Konfiguration');
      
      if (this.settings.debugMode) {
        console.error('Connection Error:', e);
      }
    }
  }

  getWebSocketURL() {
    // Environment-basierte WebSocket URL
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      
      // Development vs Production
      if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'ws://localhost:8123';
      } else {
        return `${protocol}//${hostname}:8123`;
      }
    }
    
    // Fallback
    return 'ws://raspi4.local:8123';
  }

  setupEventListeners() {
    if (typeof document === 'undefined') return;

    // Keyboard Shortcuts (Platform-agnostic)
    document.addEventListener('keydown', (event) => {
      this.handleKeyboardShortcuts(event);
    });

    // Visibility Change (für Background-Handling)
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.onAppPause();
      } else {
        this.onAppResume();
      }
    });

    // Online/Offline Events
    window.addEventListener('online', () => {
      this.updateStatus('connected', '🌐 Online - Verbindung wiederhergestellt');
      this.initializeWebSocket();
    });

    window.addEventListener('offline', () => {
      this.updateStatus('error', '📵 Offline - Keine Internetverbindung');
    });
  }

  handleKeyboardShortcuts(event) {
    // Platform-spezifische Modifier-Keys
    const modifier = this.platform === 'desktop' && navigator.platform.includes('Mac') 
      ? event.metaKey 
      : event.ctrlKey;

    // Universelle Shortcuts
    if (modifier && event.key === 'Enter') {
      event.preventDefault();
      this.toggleRecording();
    }

    if (event.key === 'Escape') {
      if (this.isRecording) {
        this.stopRecording();
      } else {
        this.closeAllMenus();
      }
    }

    if (modifier && event.key === ',') {
      event.preventDefault();
      this.openSettingsModal();
    }
  }

  closeAllMenus() {
    // Alle offenen Menüs und Modals schließen
    const settingsMenu = document.getElementById('settingsMenu');
    const settingsModal = document.getElementById('settingsModal');
    
    if (settingsMenu) settingsMenu.classList.remove('active');
    if (settingsModal) settingsModal.classList.remove('active');
  }

  onAppPause() {
    console.log('⏸️ App pausiert');
    if (this.isRecording) {
      this.stopRecording();
    }
  }

  onAppResume() {
    console.log('▶️ App fortgesetzt');
    if (this.ws && this.ws.readyState !== WebSocket.OPEN) {
      this.initializeWebSocket();
    }
  }

  // Settings Management
  loadSettings() {
    try {
      let savedSettings = null;
      
      // Platform-spezifisches Settings-Loading
      if (this.platform === 'desktop' && window.electronAPI?.store) {
        savedSettings = window.electronAPI.store.get('voice-assistant-settings');
      } else if (typeof localStorage !== 'undefined') {
        savedSettings = localStorage.getItem('voice-assistant-settings');
      }
      
      if (savedSettings) {
        const parsed = typeof savedSettings === 'string' 
          ? JSON.parse(savedSettings) 
          : savedSettings;
        
        // Merge mit Default-Settings
        this.settings = this.deepMerge(this.settings, parsed);
        console.log('✅ Einstellungen geladen');
      }
    } catch (error) {
      console.warn('⚠️ Fehler beim Laden der Einstellungen:', error);
    }
  }

  saveSettings() {
    try {
      const settingsJson = JSON.stringify(this.settings);
      
      // Platform-spezifisches Settings-Saving
      if (this.platform === 'desktop' && window.electronAPI?.store) {
        window.electronAPI.store.set('voice-assistant-settings', settingsJson);
      } else if (typeof localStorage !== 'undefined') {
        localStorage.setItem('voice-assistant-settings', settingsJson);
      }
      
      console.log('💾 Einstellungen gespeichert');
    } catch (error) {
      console.warn('⚠️ Fehler beim Speichern der Einstellungen:', error);
    }
  }

  deepMerge(target, source) {
    const result = { ...target };
    
    for (const key in source) {
      if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
        result[key] = this.deepMerge(target[key] || {}, source[key]);
      } else {
        result[key] = source[key];
      }
    }
    
    return result;
  }

  applySettings() {
    this.applyAnimationSpeed();
    this.applyNebelColors();
    this.applyGlassOpacity();
    this.applyReducedMotion();
    
    // Platform-spezifische Settings anwenden
    if (this.platform === 'mobile' && this.settings.platform.mobile.hapticFeedback) {
      this.enableHapticFeedback();
    }
  }

  applyAnimationSpeed() {
    const speed = this.settings.animationSpeed;
    if (typeof document !== 'undefined') {
      document.documentElement.style.setProperty('--animation-speed', `${4/speed}s`);
      document.documentElement.style.setProperty('--avatar-speed', `${4/speed}s`);
      document.documentElement.style.setProperty('--nebel-speed', `${3/speed}s`);
    }
  }

  applyNebelColors() {
    const colors = this.settings.nebelColors;
    
    if (typeof document !== 'undefined') {
      document.documentElement.style.setProperty('--nebel-primary', colors.primary);
      document.documentElement.style.setProperty('--nebel-secondary', colors.secondary);
      document.documentElement.style.setProperty('--nebel-accent', colors.accent);
      
      // Update element backgrounds
      this.updateNebelElementColors();
    }
  }

  updateNebelElementColors() {
    // Helper function to convert hex to rgba
    const hexToRgba = (hex, alpha) => {
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    };
    
    const colors = this.settings.nebelColors;
    
    // Update avatar nebel layers
    const avatarLayers = document.querySelectorAll('.avatar-nebel-layer');
    if (avatarLayers[0]) {
      avatarLayers[0].style.background = `radial-gradient(circle, ${hexToRgba(colors.primary, 0.6)} 0%, ${hexToRgba(colors.primary, 0.3)} 40%, transparent 70%)`;
    }
    if (avatarLayers[1]) {
      avatarLayers[1].style.background = `radial-gradient(circle, ${hexToRgba(colors.secondary, 0.5)} 0%, ${hexToRgba(colors.secondary, 0.2)} 50%, transparent 80%)`;
    }
    if (avatarLayers[2]) {
      avatarLayers[2].style.background = `radial-gradient(circle, ${hexToRgba(colors.accent, 0.4)} 0%, ${hexToRgba(colors.accent, 0.1)} 60%, transparent 90%)`;
    }
    
    // Update nebel animation circles
    const nebelCircles = document.querySelectorAll('.nebel-circle');
    if (nebelCircles[0]) {
      nebelCircles[0].style.background = `radial-gradient(circle, ${hexToRgba(colors.primary, 0.8)} 0%, ${hexToRgba(colors.primary, 0.4)} 30%, ${hexToRgba(colors.primary, 0.1)} 60%, transparent 100%)`;
    }
    if (nebelCircles[1]) {
      nebelCircles[1].style.background = `radial-gradient(circle, ${hexToRgba(colors.secondary, 0.8)} 0%, ${hexToRgba(colors.secondary, 0.4)} 30%, ${hexToRgba(colors.secondary, 0.1)} 60%, transparent 100%)`;
    }
    if (nebelCircles[2]) {
      nebelCircles[2].style.background = `radial-gradient(circle, ${hexToRgba(colors.accent, 0.8)} 0%, ${hexToRgba(colors.accent, 0.4)} 30%, ${hexToRgba(colors.accent, 0.1)} 60%, transparent 100%)`;
    }
  }

  applyGlassOpacity() {
    if (typeof document !== 'undefined') {
      document.documentElement.style.setProperty('--glass-bg', `rgba(255, 255, 255, ${this.settings.glassOpacity})`);
    }
  }

  applyReducedMotion() {
    if (typeof document !== 'undefined') {
      if (this.settings.reducedMotion) {
        document.body.classList.add('reduced-motion');
      } else {
        document.body.classList.remove('reduced-motion');
      }
    }
  }

  enableHapticFeedback() {
    if (this.platform === 'mobile' && 'vibrate' in navigator) {
      // Add haptic feedback to buttons
      document.querySelectorAll('button, .btn').forEach(button => {
        button.addEventListener('click', () => {
          navigator.vibrate(50);
        });
      });
    }
  }

  // UI Methods
  updateStatus(type, message) {
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    
    if (statusDot && statusText) {
      statusDot.className = `status-dot ${type}`;
      statusText.textContent = message;
    }
  }

  displayResponse(content) {
    const responseElement = document.getElementById('response');
    if (responseElement) {
      responseElement.innerHTML = `<div class="response-content">${content}</div>`;
      responseElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  showNebelAnimation() {
    if (this.settings.avatarAnimation) {
      this.activateAvatar();
    }
    if (this.settings.responseNebel) {
      const nebelAnimation = document.getElementById('nebelAnimation');
      const response = document.getElementById('response');
      if (nebelAnimation) nebelAnimation.classList.add('active');
      if (response) response.style.opacity = '0.3';
    }
  }

  hideNebelAnimation() {
    if (this.settings.avatarAnimation) {
      this.deactivateAvatar();
    }
    if (this.settings.responseNebel) {
      const nebelAnimation = document.getElementById('nebelAnimation');
      const response = document.getElementById('response');
      if (nebelAnimation) nebelAnimation.classList.remove('active');
      if (response) response.style.opacity = '1';
    }
  }

  activateAvatar() {
    const avatar = document.getElementById('avatar');
    if (avatar) avatar.classList.add('active');
  }

  deactivateAvatar() {
    const avatar = document.getElementById('avatar');
    if (avatar) avatar.classList.remove('active');
  }

  // Audio Recording Methods
  async startRecording() {
    if (this.isRecording) return;

    try {
      const audioSettings = {
        echoCancellation: this.settings.echoCancellation,
        noiseSuppression: this.settings.noiseSuppression,
        sampleRate: 44100
      };

      const stream = await navigator.mediaDevices.getUserMedia({ audio: audioSettings });
      
      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      const audioChunks = [];
      
      this.mediaRecorder.ondataavailable = event => {
        audioChunks.push(event.data);
      };
      
      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        const reader = new FileReader();
        
        reader.onloadend = () => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.showNebelAnimation();
            this.displayResponse("Verarbeite Spracheingabe...");
            
            this.ws.send(JSON.stringify({ 
              type: "audio", 
              content: reader.result,
              timestamp: Date.now()
            }));
          } else {
            this.showNotification('error', 'Keine Verbindung', 'Spracheingabe konnte nicht übertragen werden');
          }
        };
        
        reader.readAsDataURL(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };
      
      this.mediaRecorder.start();
      this.isRecording = true;
      this.updateRecordingUI(true);
      
      this.recordingStartTime = Date.now();
      this.recordingTimer = setInterval(() => this.updateRecordingTime(), 100);
      
      this.showNotification('success', 'Aufnahme gestartet', 'Sprechen Sie jetzt...');
      
      // Auto-stop basierend auf Settings
      setTimeout(() => {
        if (this.isRecording) this.stopRecording();
      }, this.settings.autoStopTime);
      
    } catch (err) {
      this.showNotification('error', 'Mikrofonzugriff verweigert', 'Bitte erlauben Sie den Zugriff auf das Mikrofon');
      if (this.settings.debugMode) {
        console.error('Microphone Error:', err);
      }
    }
  }

  stopRecording() {
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
      this.isRecording = false;
      this.updateRecordingUI(false);
      clearInterval(this.recordingTimer);
      this.showNotification('success', 'Aufnahme beendet', 'Wird verarbeitet...');
    }
  }

  toggleRecording() {
    if (this.isRecording) {
      this.stopRecording();
    } else {
      this.startRecording();
    }
  }

  updateRecordingUI(recording) {
    const voiceBtn = document.getElementById('voiceBtn');
    const voiceIcon = document.getElementById('voiceIcon');
    const voiceText = document.getElementById('voiceText');
    const indicator = document.getElementById('recordingIndicator');
    
    if (voiceBtn && voiceIcon && voiceText && indicator) {
      if (recording) {
        voiceBtn.classList.add('recording');
        voiceIcon.textContent = '⏹️';
        voiceText.textContent = 'Aufnahme stoppen';
        indicator.classList.add('active');
      } else {
        voiceBtn.classList.remove('recording');
        voiceIcon.textContent = '🎤';
        voiceText.textContent = 'Spracheingabe starten';
        indicator.classList.remove('active');
      }
    }
  }

  updateRecordingTime() {
    if (this.recordingStartTime) {
      const elapsed = Math.floor((Date.now() - this.recordingStartTime) / 1000);
      const recordingTime = document.getElementById('recordingTime');
      if (recordingTime) {
        recordingTime.textContent = `${elapsed}s`;
      }
    }
  }

  // Text Input Methods
  sendText() {
    const input = document.getElementById("textInput");
    const sendBtn = document.getElementById("sendBtn");
    
    if (!input || input.value.trim() === "") return;
    
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      if (sendBtn) {
        sendBtn.classList.add('loading');
        sendBtn.disabled = true;
      }
      
      this.showNebelAnimation();
      this.displayResponse("Verarbeite Ihre Anfrage...");
      
      this.ws.send(JSON.stringify({ 
        type: "text", 
        content: input.value.trim(),
        timestamp: Date.now()
      }));
      
      input.value = "";
      
      setTimeout(() => {
        if (sendBtn) {
          sendBtn.classList.remove('loading');
          sendBtn.disabled = false;
        }
      }, 1000);
    } else {
      this.showNotification('error', 'Keine Verbindung', 'Bitte warten Sie, bis die Verbindung hergestellt ist');
    }
  }

  clearResponse() {
    const responseElement = document.getElementById('response');
    if (responseElement) {
      responseElement.innerHTML = '<div class="response-empty">Ihre Antwort erscheint hier...</div>';
    }
    this.hideNebelAnimation();
    this.showNotification('success', 'Gelöscht', 'Antwort wurde gelöscht');
  }

  // Notification System (Platform-agnostic)
  showNotification(type, title, message, duration = 5000) {
    if (!this.settings.notifications) return;
    
    // Platform-spezifische Notifications
    if (this.platform === 'desktop' && window.showDesktopNotification) {
      return window.showDesktopNotification(title, message);
    }
    
    if (this.platform === 'mobile' && window.mobileNotifications) {
      return window.mobileNotifications.show(title, message);
    }
    
    // Fallback: Web GUI Notification
    this.showWebNotification(type, title, message, duration);
  }

  showWebNotification(type, title, message, duration) {
    const container = document.getElementById('notificationContainer');
    if (!container) return;
    
    const notification = document.createElement('div');
    
    notification.className = `notification ${type}`;
    notification.innerHTML = `
      <div class="notification-icon">
        ${type === 'success' ? '✅' : type === 'error' ? '❌' : '⚠️'}
      </div>
      <div class="notification-content">
        <div class="notification-title">${title}</div>
        <div class="notification-message">${message}</div>
      </div>
      <button class="notification-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    container.appendChild(notification);
    
    // Animate in
    setTimeout(() => notification.classList.add('show'), 100);
    
    // Auto remove
    setTimeout(() => {
      if (notification.parentElement) {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
      }
    }, duration);
  }

  // Settings Modal Methods
  openSettingsModal() {
    const modal = document.getElementById('settingsModal');
    if (modal) {
      modal.classList.add('active');
      this.loadSettingsUI();
    }
  }

  closeSettingsModal() {
    const modal = document.getElementById('settingsModal');
    if (modal) {
      modal.classList.remove('active');
    }
  }

  loadSettingsUI() {
    // Load current settings into UI elements
    // This will be called by the platform-specific implementations
    console.log('📋 Loading Settings UI...');
  }

  // System Information
  async getSystemInfo() {
    const baseInfo = {
      platform: this.platform,
      userAgent: navigator.userAgent,
      language: navigator.language,
      online: navigator.onLine,
      cookieEnabled: navigator.cookieEnabled,
      version: '2.1.0'
    };

    // Platform-spezifische System-Infos
    if (this.platform === 'desktop' && window.desktopApp) {
      return { ...baseInfo, ...(await window.desktopApp.getDesktopSystemInfo()) };
    }

    if (this.platform === 'mobile' && window.mobileApp) {
      return { ...baseInfo, ...window.mobileApp.getDeviceInfo() };
    }

    return baseInfo;
  }
}

// Global instance
let voiceAssistant = null;

// Initialize when DOM is ready
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', async () => {
    voiceAssistant = new VoiceAssistantCore();
    await voiceAssistant.initialize();
    
    // Make globally available
    window.voiceAssistant = voiceAssistant;
    
    // Setup global functions for UI
    window.sendText = () => voiceAssistant.sendText();
    window.toggleRecording = () => voiceAssistant.toggleRecording();
    window.clearResponse = () => voiceAssistant.clearResponse();
    window.openSettingsModal = () => voiceAssistant.openSettingsModal();
    window.closeSettingsModal = () => voiceAssistant.closeSettingsModal();
    
    // Focus auf Eingabefeld
    const textInput = document.getElementById('textInput');
    if (textInput) textInput.focus();
  });
}

// Export für Module-Systeme
if (typeof module !== 'undefined' && module.exports) {
  module.exports = VoiceAssistantCore;
}
