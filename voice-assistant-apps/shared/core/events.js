/**
 * Event Handlers - UI Interaktionen & App Logic
 * 
 * Zentrale Event-Handler für alle UI-Interaktionen
 * - Text senden & Spracheingabe
 * - Avatar Interaktionen
 * - Recording Management
 * - Theme & Settings
 * - Keyboard Shortcuts
 */

import { DOMHelpers } from './dom-helpers.js';
import Backend from './backend.js';
import AudioManager from './audio.js';
import Settings from './settings.js';

/**
 * Event State Management
 */
const EventState = {
  // Recording State
  isRecording: false,
  recordingTimer: null,
  recordingStartTime: null,
  autoStopTimer: null,
  
  // UI State
  sidebarOpen: false,
  currentTheme: 'dark',
  
  // Avatar State
  currentEmotion: 'idle',
  
  // Settings
  settings: {
    voiceVisualization: true,
    notifications: true,
    vadEnabled: true,
    autoStop: true,
    maxRecordMs: 30000
  }
};

/**
 * Notification System
 */
export const NotificationManager = {
  /**
   * Notification anzeigen
   * @param {string} type - success, error, warning, info
   * @param {string} title - Titel
   * @param {string} message - Nachricht
   * @param {number} duration - Anzeigedauer in ms
   */
  show(type, title, message, duration = 4000) {
    if (!EventState.settings.notifications) return;

    const container = DOMHelpers.$('#notificationContainer');
    if (!container) return;

    const notification = DOMHelpers.createElement('div', {
      className: `notification ${type}`
    });

    const iconMap = {
      success: '✅',
      error: '❌', 
      warning: '⚠️',
      info: 'ℹ️'
    };

    notification.innerHTML = `
      <div class="notification-icon">${iconMap[type] || 'ℹ️'}</div>
      <div class="notification-content">
        <div class="notification-title">${title}</div>
        <div class="notification-message">${message}</div>
      </div>
      <button class="notification-close" type="button" aria-label="Schließen">×</button>
    `;

    container.appendChild(notification);
    const closeBtn = notification.querySelector('.notification-close');
    if (closeBtn) closeBtn.addEventListener('click', () => NotificationManager.close(closeBtn));
    // Animate in
    setTimeout(function() {
      DOMHelpers.toggleClass(notification, 'show', true);
    }, 100);

    // Auto remove
    setTimeout(function() {
      NotificationManager.close(notification.querySelector('.notification-close'));
    }, duration);
  },

  /**
   * Notification schließen
   * @param {Element} closeButton 
   */
  close(closeButton) {
    const notification = closeButton.closest('.notification');
    if (notification) {
      DOMHelpers.toggleClass(notification, 'show', false);
      setTimeout(function() {
        notification.remove();
      }, 400);
    }
  }
};

/**
 * Avatar Emotion System
 */
export const AvatarManager = {
  /**
   * Avatar Emotion setzen
   * @param {string} emotion - idle, listening, thinking, speaking, error, happy
   */
  setEmotion(emotion) {
    const avatar = DOMHelpers.$('#avatar');
    if (!avatar) return;

    // Alte Emotionen entfernen
    const emotions = ['idle', 'listening', 'thinking', 'speaking', 'error', 'happy'];
    emotions.forEach(function(emo) {
      DOMHelpers.toggleClass(avatar, emo, false);
    });

    // Neue Emotion setzen
    DOMHelpers.toggleClass(avatar, emotion, true);
    EventState.currentEmotion = emotion;

    console.log('Avatar Emotion:', emotion);
  },

  /**
   * Processing Animation zeigen/verstecken
   * @param {boolean} show 
   */
  showProcessing(show) {
    const animation = DOMHelpers.$('#processingAnimation');
    if (animation) {
      DOMHelpers.toggleClass(animation, 'active', show);
    }
  },

  /**
   * Response im Avatar anzeigen
   * @param {string} content 
   */
  showResponse(content) {
    const responseEl = DOMHelpers.$('#responseContent');
    if (!responseEl) return;

    AvatarManager.showProcessing(false);

    if (!content || content === "Ihre Antwort erscheint hier...") {
      DOMHelpers.setHTML(responseEl, '<div class="response-empty">Ihre Antwort erscheint hier...</div>');
      DOMHelpers.toggleClass(responseEl, 'show', false);
      return;
    }

    // Matrix Rain Effekt
    DOMHelpers.toggleClass(responseEl, 'show', true);
    AvatarManager.matrixRainEffect(responseEl, content);
  },

  /**
   * Matrix Rain Texteffekt
   * @param {Element} element 
   * @param {string} text 
   */
  matrixRainEffect(element, text) {
    const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let iteration = 0;

    const interval = setInterval(function() {
      const scrambledText = text
        .split('')
        .map(function(char, index) {
          if (index < iteration) {
            return char;
          }
          return letters[Math.floor(Math.random() * letters.length)];
        })
        .join('');

      DOMHelpers.setText(element, scrambledText);

      if (iteration >= text.length) {
        clearInterval(interval);
        DOMHelpers.setText(element, text);
      }
      iteration += 1;
    }, 30);
  }
};

/**
 * Recording Event Handlers
 */
export const RecordingEvents = {
  /**
   * Aufnahme starten
   */
  async startRecording() {
    if (EventState.isRecording) return;

    try {
      console.log('Starte Aufnahme...');
      
      // UI aktualisieren
      RecordingEvents.updateRecordingUI(true);
      AvatarManager.setEmotion('listening');
      
      // Audio-Aufnahme starten
      await AudioManager.startRecording({
        enableVisualization: EventState.settings.voiceVisualization,
        echoCancellation: Settings.get('echoCancellation') !== false,
        noiseSuppression: Settings.get('noiseSuppression') !== false,
        autoGainControl: true,
        deviceId: Settings.get('micDeviceId') || undefined,
        onAudioReady: function(audioDataUrl) {
          RecordingEvents.handleAudioReady(audioDataUrl);
        }
      });

      EventState.isRecording = true;
      EventState.recordingStartTime = Date.now();
      
      // Recording Timer starten
      RecordingEvents.startRecordingTimer();

      // Optionales Auto-Stop nach maxRecordMs
      if (EventState.settings.autoStop) {
        if (EventState.autoStopTimer) { clearTimeout(EventState.autoStopTimer); EventState.autoStopTimer = null; }
        EventState.autoStopTimer = setTimeout(function() {
          if (EventState.isRecording) RecordingEvents.stopRecording();
        }, Math.max(5000, EventState.settings.maxRecordMs || 30000));
      }

      NotificationManager.show('success', 'Aufnahme gestartet', 'Sprechen Sie jetzt...');

    } catch (error) {
      console.error('Aufnahme Start Fehler:', error);
      NotificationManager.show('error', 'Aufnahme fehlgeschlagen', error.message);
      AvatarManager.setEmotion('error');
      setTimeout(function() { AvatarManager.setEmotion('idle'); }, 2000);
    }
  },

  /**
   * Aufnahme stoppen
   */
  async stopRecording() {
    if (!EventState.isRecording) return;

    try {
      console.log('Stoppe Aufnahme...');

      await AudioManager.stopRecording();
      
      EventState.isRecording = false;
      RecordingEvents.updateRecordingUI(false);
      RecordingEvents.stopRecordingTimer();
      if (EventState.autoStopTimer) { clearTimeout(EventState.autoStopTimer); EventState.autoStopTimer = null; }

      AvatarManager.setEmotion('thinking');
      AvatarManager.showProcessing(true);

      NotificationManager.show('success', 'Aufnahme beendet', 'Wird verarbeitet...');

    } catch (error) {
      console.error('Aufnahme Stop Fehler:', error);
      NotificationManager.show('error', 'Aufnahme Stop fehlgeschlagen', error.message);
    }
  },

  /**
   * Recording UI aktualisieren
   * @param {boolean} recording 
   */
  updateRecordingUI(recording) {
    const voiceBtn = DOMHelpers.$('#voiceBtn');
    const voiceIcon = DOMHelpers.$('#voiceIcon');
    const indicator = DOMHelpers.$('#recordingIndicator');

    if (voiceBtn) {
      DOMHelpers.toggleClass(voiceBtn, 'recording', recording);
      // Fallback: Icon direkt im Button aktualisieren, wenn kein #voiceIcon vorhanden ist
      if (!voiceIcon) {
        try { voiceBtn.textContent = recording ? '⏹️' : '🎙️'; } catch (_) {}
      }
    }
    
    if (voiceIcon) {
      DOMHelpers.setText(voiceIcon, recording ? '⏹️' : '🎤');
    }
    
    if (indicator) {
      DOMHelpers.toggleClass(indicator, 'active', recording);
    }
  },

  /**
   * Recording Timer starten
   */
  startRecordingTimer() {
    EventState.recordingTimer = setInterval(function() {
      if (EventState.recordingStartTime) {
        const elapsed = Math.floor((Date.now() - EventState.recordingStartTime) / 1000);
        const timeElement = DOMHelpers.$('#recordingTime');
        if (timeElement) {
          DOMHelpers.setText(timeElement, elapsed + 's');
        }
      }
    }, 100);
  },

  /**
   * Recording Timer stoppen
   */
  stopRecordingTimer() {
    if (EventState.recordingTimer) {
      clearInterval(EventState.recordingTimer);
      EventState.recordingTimer = null;
    }
  },

  /**
   * Audio bereit Handler
   * @param {string} audioDataUrl 
   */
  handleAudioReady(audioDataUrl) {
    console.log('Audio bereit für Übertragung');
    Backend.sendAudio(audioDataUrl);
  }
};

/**
 * Text Input Events
 */
export const TextEvents = {
  /**
   * Text senden
   */
  sendText() {
    const input = DOMHelpers.$('#textInput');
    if (!input || !input.value.trim()) return;

    const text = input.value.trim();
    input.value = '';

    console.log('Sende Text:', text);

    // UI Feedback
    AvatarManager.setEmotion('thinking');
    AvatarManager.showProcessing(true);
    AvatarManager.showResponse(`Verarbeite: "${text}"`);

    // An Backend senden
    if (Backend.sendText(text)) {
      NotificationManager.show('info', 'Nachricht gesendet', 'Warte auf Antwort...');
    } else {
      NotificationManager.show('error', 'Senden fehlgeschlagen', 'Keine Verbindung zum Server');
      AvatarManager.setEmotion('error');
      setTimeout(function() { AvatarManager.setEmotion('idle'); }, 2000);
    }
  },

  /**
   * Input Keypress Handler
   * @param {KeyboardEvent} event 
   */
  handleInputKeypress(event) {
    if (event.key === 'Enter') {
      event.preventDefault();
      TextEvents.sendText();
    }
  }
};

/**
 * Theme Management
 */
export const ThemeManager = {
  themes: ['dark', 'light', 'sci-fi', 'nature', 'high-contrast'],
  
  /**
   * Theme wechseln
   * @param {string} theme 
   */
  setTheme(theme) {
    if (!ThemeManager.themes.includes(theme)) {
      console.warn('Unbekanntes Theme:', theme);
      return;
    }

    document.body.setAttribute('data-theme', theme);
    EventState.currentTheme = theme;
    
    // Theme Icon aktualisieren
    const themeBtn = DOMHelpers.$('#themeToggle');
    if (themeBtn) {
      const icons = {
        dark: '☀️',
        light: '🌙',
        'sci-fi': '🚀',
        nature: '🌿',
        'high-contrast': '🔲'
      };
      DOMHelpers.setText(themeBtn, icons[theme] || '☀️');
    }

    // In localStorage speichern
    try {
      localStorage.setItem('va.settings.theme', theme);
    } catch (e) {
      console.warn('Theme speichern fehlgeschlagen:', e);
    }

    NotificationManager.show('success', 'Theme geändert', theme.charAt(0).toUpperCase() + theme.slice(1));
  },

  /**
   * Nächstes Theme
   */
  cycleTheme() {
    const currentIndex = ThemeManager.themes.indexOf(EventState.currentTheme);
    const nextIndex = (currentIndex + 1) % ThemeManager.themes.length;
    ThemeManager.setTheme(ThemeManager.themes[nextIndex]);
  },

  /**
   * Theme aus localStorage laden
   */
  loadTheme() {
    try {
      const savedTheme = localStorage.getItem('va.settings.theme');
      if (savedTheme && ThemeManager.themes.includes(savedTheme)) {
        ThemeManager.setTheme(savedTheme);
      }
    } catch (e) {
      console.warn('Theme laden fehlgeschlagen:', e);
    }
  }
};

/**
 * Sidebar Events
 */
export const SidebarEvents = {
  /**
   * Sidebar toggle
   */
  toggleSidebar() {
    EventState.sidebarOpen = !EventState.sidebarOpen;
    
    const sidebar = DOMHelpers.$('#sidebar');
    const toggleBtn = DOMHelpers.$('#sidebarToggle');
    
    if (sidebar) {
      DOMHelpers.toggleClass(sidebar, 'open', EventState.sidebarOpen);
    }
    
    if (toggleBtn) {
      DOMHelpers.toggleClass(toggleBtn, 'active', EventState.sidebarOpen);
    }
    
    DOMHelpers.toggleClass(document.body, 'sidebar-open', EventState.sidebarOpen);

    console.log('Sidebar:', EventState.sidebarOpen ? 'geöffnet' : 'geschlossen');
  }
};

/**
 * App Events - Hauptklasse
 */
export const AppEvents = {
  /**
   * Text senden
   */
  sendText() {
    TextEvents.sendText();
  },

  /**
   * Recording toggle
   */
  toggleRecording() {
    if (EventState.isRecording) {
      RecordingEvents.stopRecording();
    } else {
      RecordingEvents.startRecording();
    }
  },

  /**
   * Avatar Click Handler
   */
  handleAvatarClick() {
    // Avatar klick = Recording toggle
    AppEvents.toggleRecording();
    
    // Happy Feedback
    AvatarManager.setEmotion('happy');
    setTimeout(function() { 
      if (!EventState.isRecording) {
        AvatarManager.setEmotion('idle'); 
      }
    }, 1000);
  },

  /**
   * Input Keypress
   * @param {KeyboardEvent} event 
   */
  handleInputKeypress(event) {
    TextEvents.handleInputKeypress(event);
  },

  /**
   * Sidebar toggle
   */
  toggleSidebar() {
    SidebarEvents.toggleSidebar();
  },

  /**
   * Theme cycle
   */
  cycleTheme() {
    ThemeManager.cycleTheme();
  },

  /**
   * Info anzeigen
   */
  showInfo() {
    const info = `
KI-Sprachassistent v2.1.0
Platform: ${navigator.platform}
WebSocket: ${Backend.getStatus().connected ? 'Verbunden' : 'Getrennt'}
Audio: ${AudioManager.getSettings ? 'Aktiv' : 'Inaktiv'}
Theme: ${EventState.currentTheme}
    `;
    
    NotificationManager.show('info', 'System-Information', info, 8000);
  },

  /**
   * Backend Message Handler
   * @param {Object} data 
   */
  handleBackendMessage(data) {
    console.log('Backend Message:', data);

    switch (data.type) {
      case 'response':
      case 'final_text':
        if (data.content || data.text) {
          const content = data.content || data.text;
          AvatarManager.showResponse(content);
          AvatarManager.setEmotion('speaking');
          
          // Nach 3 Sekunden zurück zu idle
          setTimeout(function() {
            AvatarManager.setEmotion('idle');
          }, 3000);
        }
        break;

      case 'audio_response':
      case 'tts':
        if (data.audio) {
          // TTS Audio abspielen
          AudioManager.playTts(data.audio).catch(function(error) {
            console.error('TTS Playback Fehler:', error);
            NotificationManager.show('error', 'Audio Fehler', 'TTS Wiedergabe fehlgeschlagen');
          });
        }
        break;

      case 'tts_chunk':
        try {
          let prog = document.getElementById('ttsProgress');
          if (!prog) {
            prog = document.createElement('div');
            prog.id = 'ttsProgress';
            prog.className = 'tts-progress show';
            const badge = document.createElement('span'); badge.id = 'ttsEngineBadge'; badge.className = 'tts-badge';
            const count = document.createElement('span'); count.id = 'ttsCount';
            const bar = document.createElement('div'); bar.className = 'tts-bar';
            const fill = document.createElement('span'); fill.id = 'ttsFill'; bar.appendChild(fill);
            prog.appendChild(badge); prog.appendChild(count); prog.appendChild(bar);
            const host = document.getElementById('responseContent') || document.body;
            host.parentNode.insertBefore(prog, host.nextSibling);
          }
          prog.classList.add('show');
          const badge = document.getElementById('ttsEngineBadge');
          const count = document.getElementById('ttsCount');
          const fill = document.getElementById('ttsFill');
          if (badge) badge.textContent = (data.engine || '').toUpperCase();
          if (count) count.textContent = ` ${Number(data.index)+1}/${Number(data.total)||2}`;
          if (fill) {
            const pct = Math.min(100, Math.max(0, Math.round(((Number(data.index)+1) / (Number(data.total)||2)) * 100)));
            fill.style.width = pct + '%';
          }
        } catch (e) { console.warn('tts_progress UI error:', e); }
        try { AudioManager.addTtsChunk(data); } catch (e) { console.warn('tts_chunk Fehler:', e); }
        break;

      case 'tts_sequence_end':
        try { AudioManager.endTtsSequence(data); } catch (_) {}
        try { const prog = document.getElementById('ttsProgress'); if (prog) setTimeout(() => prog.classList.remove('show'), 800); } catch (_) {}
        break;

      case 'staged_tts_config_updated':
        try {
          const cfg = data.config || {};
          const status = document.getElementById('ttsPlanStatus');
          if (status) {
            status.textContent = `Aktiv: ${cfg.intro_engine || 'piper'} → ${cfg.main_engine || 'zonos'} · Crossfade ${cfg.crossfade_ms || 100}ms · Intro ${cfg.max_intro_length || 120}`;
          }
          const btn = document.getElementById('applyTtsPlan');
          if (btn) btn.disabled = false;
          NotificationManager.show('success', 'Staged TTS', 'Plan angewendet');
        } catch (_) {}
        break;
      case 'progress':
        console.log(`[TTS] ${data.phase} ${Number(data.index)+1}/${data.total} via ${data.engine}`);
        break;
      case 'log':
        console.log('[Backend]', data.message);
        break;
      case 'ok':
        // Ack – ignorieren
        break;
      // dynamic voice list messages removed; GUI uses static list

      case 'error':
        const errorMsg = data.message || data.error || 'Unbekannter Fehler';
        NotificationManager.show('error', 'Server Fehler', errorMsg);
        AvatarManager.setEmotion('error');
        setTimeout(function() { AvatarManager.setEmotion('idle'); }, 2000);
        break;

      case 'binary':
        // Binary Audio Data (für advanced playback)
        console.log('Binary Audio Data empfangen:', data.data.byteLength, 'bytes');
        break;

      default:
        console.log('Unbekannte Message:', data.type);
    }
  },

  /**
   * Backend Connected Handler
   */
  handleBackendConnected() {
    console.log('Backend verbunden');
    NotificationManager.show('success', 'Verbunden', 'WebSocket Verbindung hergestellt');
    AvatarManager.setEmotion('happy');
    setTimeout(function() { AvatarManager.setEmotion('idle'); }, 2000);
  },

  /**
   * Backend Disconnected Handler
   * @param {CloseEvent} event 
   */
  handleBackendDisconnected(event) {
    console.log('Backend getrennt:', event.code);
    NotificationManager.show('error', 'Verbindung getrennt', 'WebSocket Verbindung verloren');
    AvatarManager.setEmotion('error');
  },

  /**
   * LLM Models Handler
   * @param {Array} models 
   */
  handleLlmModels(models) {
    console.log('LLM Models verfügbar:', models);
    if (models.length > 0) {
      NotificationManager.show('info', 'LLM bereit', `${models.length} Modell(e) verfügbar`);
    }
  }
};

// Globale Verfügbarkeit für onclick Handler
window.App = AppEvents;
window.NotificationManager = NotificationManager;
window.AvatarManager = AvatarManager;
window.ThemeManager = ThemeManager;

export default AppEvents;
// --- CSP-safe bindings (fallback) ---
// Use DOMHelpers.ready so bindings run even if DOMContentLoaded already fired
importReadyBindings:
DOMHelpers.ready(() => {
  const byId = (id) => document.getElementById(id);

  const sendBtn   = byId('sendBtn');
  const voiceBtn  = byId('voiceBtn');
  const inputEl   = byId('textInput');
  const toggleBtn = byId('sidebarToggle');

  if (sendBtn && window.App?.sendText) {
    sendBtn.addEventListener('click', () => window.App.sendText());
  }
  if (voiceBtn && window.App?.toggleRecording) {
    voiceBtn.addEventListener('click', () => window.App.toggleRecording());
  }
  if (inputEl && window.App?.sendText) {
    inputEl.addEventListener('keydown', (e) => {
      if ((e.key === 'Enter' || e.keyCode === 13) && !e.shiftKey) {
        e.preventDefault();
        window.App.sendText();
      }
    });
  }
  if (toggleBtn && window.sidebarManager?.open && window.sidebarManager?.close) {
    toggleBtn.addEventListener('click', () => {
      if (document.body.classList.contains('sidebar-open')) {
        window.sidebarManager.close();
      } else {
        window.sidebarManager.open();
      }
    });
  }
});
