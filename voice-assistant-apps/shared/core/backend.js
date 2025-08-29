/**
 * Backend Communication - WebSocket & HTTP
 *
 * Verwaltet Verbindungen zum Sprachassistent-Backend
 * - WebSocket für Echtzeit
 * - HTTP für REST
 * - Auto-Reconnect & robustes Error-Handling
 * - LM Studio Auto-Discovery
 */

import { DOMHelpers } from './dom-helpers.js';

/* -------------------------- LM Studio Auto-Discovery ------------------------- */

/**
 * Ermittelt automatisch die erreichbare LM-Studio API-Base (…/v1) und
 * speichert sie in BackendConfig.llmApiBase (und localStorage).
 */
async function detectLlmApiBase() {
  const candidates = [];

  // 1) ENV aus Electron-Bridge
  try {
    const envBase = (window.electronAPI && window.electronAPI.getEnv)
      ? (window.electronAPI.getEnv('OPENAI_API_BASE') || '')
      : '';
    if (envBase) candidates.push(envBase.replace(/\/+$/, ''));
  } catch (_) {}

  // 2) localStorage
  try {
    const lsBase = localStorage.getItem('llmApiBase') || '';
    if (lsBase) candidates.push(lsBase.replace(/\/+$/, ''));
  } catch (_) {}

  // 3) Gängige Hosts / Ports von LM Studio
  const host = (typeof location !== 'undefined' && location.hostname) ? location.hostname : '127.0.0.1';
  candidates.push(
    'http://127.0.0.1:1234',
    'http://localhost:1234',
    `http://${host}:1234`,
    'http://192.168.0.45:1234'
  );

  // 4) Normalisieren auf /v1 und Duplikate entfernen
  const uniq = [...new Set(candidates)].map(b => b.endsWith('/v1') ? b : (b + '/v1'));

  for (const base of uniq) {
    try {
      const res = await fetch(base + '/models', {
        method: 'GET',
        headers: { 'Authorization': 'Bearer lm-studio' },
        cache: 'no-store'
      });
      if (res.ok) {
        window.BackendConfig = window.BackendConfig || {};
        window.BackendConfig.llmApiBase = base;
        try { localStorage.setItem('llmApiBase', base); } catch (_) {}
        console.log('[LLM] API erkannt:', base);
        return base;
      }
    } catch (_) {}
  }

  console.warn('[LLM] Keine LM Studio API gefunden - LLM Features deaktiviert.');
  window.BackendConfig = window.BackendConfig || {};
  window.BackendConfig.llmApiBase = '';
  return '';
}

/* ----------------------------- Konfiguration -------------------------------- */

const BackendConfig = {
  // Basis URLs (überschreibbar per ENV/localStorage)
  defaultHost: '127.0.0.1',
  defaultPort: '48232',

  // LM Studio
  llmApiBase: null,    // wird von detectLlmApiBase() gesetzt
  llmHost: '127.0.0.1',
  llmPort: '1234',

  // Verbindungs-Settings
  reconnectAttempts: 0,
  maxReconnectAttempts: 10,
  reconnectDelay: 1000,
  connectionTimeout: 5000,

  // WebSocket State
  ws: null,
  isConnected: false,

  // Init-Guard
  initialized: false
};

/* --------------------------------- Utils ------------------------------------ */

export const BackendUtils = {
  /**
   * Ermittelt Backend-Base-URL (http/https)
   * @returns {string}
   */
  getHttpBase() {
    // Electron ENV über preload-Bridge?
    if (typeof window !== 'undefined' && window.electronAPI?.getEnv) {
      const envBackendUrl = window.electronAPI.getEnv('BACKEND_URL');
      if (envBackendUrl) {
        try {
          const u = new URL(envBackendUrl);
          return `${u.protocol}//${u.host}`;
        } catch (e) {
          console.warn('Invalid BACKEND_URL:', envBackendUrl);
        }
      }
    }

    // Fallback: localStorage
    const host = (typeof localStorage !== 'undefined' && localStorage.getItem('wsHost')) || BackendConfig.defaultHost;
    const port = (typeof localStorage !== 'undefined' && localStorage.getItem('wsPort')) || BackendConfig.defaultPort;
    const proto = (typeof window !== 'undefined' && window.location?.protocol === 'https:') ? 'https:' : 'http:';
    return `${proto}//${host}:${port}`;
  },

  /**
   * Ermittelt WebSocket-URL (?token=… angehängt)
   * @returns {string}
   */
  getWsUrl() {
    // Electron ENV?
    if (typeof window !== 'undefined' && window.electronAPI?.getEnv) {
      const envBackendUrl = window.electronAPI.getEnv('BACKEND_URL');
      if (envBackendUrl) {
        try {
          const u = new URL(envBackendUrl);
          const proto = (u.protocol === 'https:') ? 'wss:' : 'ws:';
          return `${proto}//${u.host}/ws?token=${encodeURIComponent(this.getAuthToken())}`;
        } catch (e) {
          console.warn('Invalid BACKEND_URL:', envBackendUrl);
        }
      }
    }

    // Fallback: localStorage
    const host = (typeof localStorage !== 'undefined' && localStorage.getItem('wsHost')) || BackendConfig.defaultHost;
    const port = (typeof localStorage !== 'undefined' && localStorage.getItem('wsPort')) || BackendConfig.defaultPort;
    const proto = (typeof window !== 'undefined' && window.location?.protocol === 'https:') ? 'wss:' : 'ws:';
    return `${proto}//${host}:${port}/ws?token=${encodeURIComponent(this.getAuthToken())}`;
  },

  /**
   * Token-Auflösung
   */
  getAuthToken() {
    if (typeof localStorage === 'undefined') return 'devsecret';
    return localStorage.getItem('voice_auth_token')
        || localStorage.getItem('wsToken')
        || 'devsecret';
  },

  /**
   * LM Studio API-Base zurückgeben (ggf. aus detectLlmApiBase)
   */
  getLlmApiUrl() {
    if (BackendConfig.llmApiBase) return BackendConfig.llmApiBase;

    // Electron ENV?
    if (typeof window !== 'undefined' && window.electronAPI?.getEnv) {
      const env = window.electronAPI.getEnv('OPENAI_API_BASE');
      if (env) {
        BackendConfig.llmApiBase = env.replace(/\/+$/, '').endsWith('/v1') ? env.replace(/\/+$/, '') : (env.replace(/\/+$/, '') + '/v1');
        return BackendConfig.llmApiBase;
      }
    }

    // localStorage?
    if (typeof localStorage !== 'undefined') {
      const ls = localStorage.getItem('llmApiBase');
      if (ls) {
        BackendConfig.llmApiBase = ls.replace(/\/+$/, '');
        return BackendConfig.llmApiBase;
      }
    }

    // Fallback: aus Host/Port
    const base = `http://${BackendConfig.llmHost}:${BackendConfig.llmPort}/v1`;
    BackendConfig.llmApiBase = base;
    return base;
  }
};

/* ------------------------------ WebSocket ----------------------------------- */

export const WebSocketManager = {
  async initWebSocket(onMessage, onConnect, onDisconnect) {
    if (BackendConfig.ws && BackendConfig.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket bereits verbunden');
      return BackendConfig.ws;
    }

    return new Promise((resolve, reject) => {
      try {
        const wsUrl = BackendUtils.getWsUrl();
        console.log('Verbinde mit WebSocket:', wsUrl);

        const ws = new WebSocket(wsUrl);
        BackendConfig.ws = ws;
        ws.binaryType = 'arraybuffer';

        const to = setTimeout(() => {
          if (ws.readyState !== WebSocket.OPEN) {
            try { ws.close(); } catch (_) {}
            reject(new Error('WebSocket Connection Timeout'));
          }
        }, BackendConfig.connectionTimeout);

        ws.onopen = () => {
          clearTimeout(to);
          BackendConfig.isConnected = true;
          BackendConfig.reconnectAttempts = 0;

          // Handshake
          this.sendMessage({
            op: 'hello',
            version: 1,
            stream_id: this.generateStreamId(),
            device: this.detectPlatform(),
            stt_model: (typeof localStorage !== 'undefined' && localStorage.getItem('sttModel')) || 'base',
            tts_engine: (typeof localStorage !== 'undefined' && localStorage.getItem('ttsEngine')) || 'piper'
          });

          onConnect && onConnect();
          resolve(ws);
        };

        ws.onmessage = (ev) => {
          try {
            if (ev.data instanceof ArrayBuffer) {
              onMessage && onMessage({ type: 'binary', data: ev.data });
              return;
            }
            const data = JSON.parse(ev.data);
            if (data.op === 'ready') {
              console.log('Backend bereit:', data);
            } else if (data.type === 'pong') {
              const latency = Date.now() - (data.timestamp || Date.now());
              console.log('Pong empfangen, Latenz:', latency + 'ms');
            }
            onMessage && onMessage(data);
          } catch (e) {
            console.error('Message Parse Fehler:', e);
          }
        };

        ws.onclose = (ev) => {
          BackendConfig.isConnected = false;
          console.log('WebSocket geschlossen:', ev.code, ev.reason);
          onDisconnect && onDisconnect(ev);

          // Auto-Reconnect außer bei normaler Schließung
          if (ev.code !== 1000 && BackendConfig.reconnectAttempts < BackendConfig.maxReconnectAttempts) {
            this.scheduleReconnect(onMessage, onConnect, onDisconnect);
          }
        };

        ws.onerror = (err) => {
          console.error('WebSocket Fehler:', err);
          clearTimeout(to);
          reject(err);
        };

      } catch (err) {
        console.error('WebSocket Init Fehler:', err);
        reject(err);
      }
    });
  },

  sendMessage(message) {
    const ws = BackendConfig.ws;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket nicht verbunden, verwerfe Message:', message);
      return false;
    }
    try {
      ws.send(JSON.stringify({ timestamp: Date.now(), ...message }));
      return true;
    } catch (e) {
      console.error('Send Message Fehler:', e);
      return false;
    }
  },

  scheduleReconnect(onMessage, onConnect, onDisconnect) {
    BackendConfig.reconnectAttempts += 1;
    const delay = Math.min(BackendConfig.reconnectDelay * Math.pow(2, BackendConfig.reconnectAttempts - 1), 30000);
    console.log(`Reconnect in ${delay}ms (Versuch ${BackendConfig.reconnectAttempts}/${BackendConfig.maxReconnectAttempts})`);
    setTimeout(() => this.initWebSocket(onMessage, onConnect, onDisconnect), delay);
  },

  close() {
    try { BackendConfig.ws?.close(1000, 'Normal closure'); } catch (_) {}
    BackendConfig.ws = null;
    BackendConfig.isConnected = false;
  },

  getStatus() {
    return {
      connected: BackendConfig.isConnected,
      readyState: BackendConfig.ws ? BackendConfig.ws.readyState : WebSocket.CLOSED,
      reconnectAttempts: BackendConfig.reconnectAttempts,
      url: BackendUtils.getWsUrl()
    };
  },

  generateStreamId() {
    return (typeof crypto !== 'undefined' && crypto.randomUUID)
      ? crypto.randomUUID()
      : `stream_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
  },

  detectPlatform() {
    if (typeof window !== 'undefined' && window.electronAPI) return 'desktop';
    if (typeof navigator !== 'undefined' && /Mobile|Android|iPhone|iPad/i.test(navigator.userAgent)) return 'mobile';
    return 'web';
  }
};

/* ---------------------------------- HTTP ------------------------------------ */

export const HttpManager = {
  async request(url, options = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.timeout || BackendConfig.connectionTimeout);

    try {
      const res = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {})
        }
      });
      clearTimeout(timeoutId);
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      return await res.json();
    } catch (e) {
      clearTimeout(timeoutId);
      if (e.name === 'AbortError') throw new Error('Request timeout');
      throw e;
    }
  },

  async healthCheck() {
    try {
      const url = BackendUtils.getHttpBase() + '/health';
      const res = await this.request(url, { timeout: 3000 });
      return !!(res && res.status === 'ok');
    } catch (e) {
      console.warn('Health check failed:', e.message);
      return false;
    }
  },

  async getLlmModels() {
    try {
      const url = BackendUtils.getLlmApiUrl() + '/models';
      const res = await this.request(url, {
        timeout: 10000,
        headers: { 'Authorization': 'Bearer lm-studio' }
      });
      if (res && res.data) {
        return res.data.map(m => m.id || m.name || 'unknown');
      }
      return [];
    } catch (e) {
      console.warn('LLM Models abrufen fehlgeschlagen:', e.message);
      return [];
    }
  },

  async sendLlmMessage(message, model) {
    try {
      const url = BackendUtils.getLlmApiUrl() + '/chat/completions';
      const res = await this.request(url, {
        method: 'POST',
        timeout: 30000,
        headers: { 'Authorization': 'Bearer lm-studio' },
        body: JSON.stringify({
          model: model || 'liquid/lfm2-1.2b',
          messages: [{ role: 'user', content: message }],
          temperature: 0.7,
          max_tokens: 500,
          stream: false
        })
      });
      if (res && res.choices && res.choices[0] && res.choices[0].message) {
        return res.choices[0].message.content;
      }
      throw new Error('Invalid LLM response format');
    } catch (e) {
      console.error('LLM Request failed:', e.message);
      throw e;
    }
  }
};

/* --------------------------------- Backend ---------------------------------- */

export const Backend = {
  // State für App-Integration
  isRecording: false,

  /**
   * Convenience-Wrapper: ruft init() mit Default-Handlern auf
   */
  async initialize() {
    console.log('Backend wird initialisiert...');
    const handlers = {
      onMessage: this.defaultMessageHandler.bind(this),
      onConnect: this.defaultConnectHandler.bind(this),
      onDisconnect: this.defaultDisconnectHandler.bind(this),
      onLlmModels: this.defaultLlmModelsHandler.bind(this)
    };
    return this.init(handlers);
  },

  /**
   * Backend initialisieren
   * @param {Object} handlers
   */
  async init(handlers = {}) {
    // Fallback: ensure default handlers if none provided
    if (!handlers || typeof handlers !== 'object') handlers = {};
    handlers.onMessage = handlers.onMessage || this.defaultMessageHandler.bind(this);
    handlers.onConnect = handlers.onConnect || this.defaultConnectHandler.bind(this);
    handlers.onDisconnect = handlers.onDisconnect || this.defaultDisconnectHandler.bind(this);
    handlers.onLlmModels = handlers.onLlmModels || this.defaultLlmModelsHandler.bind(this);
    try { await detectLlmApiBase(); } catch (_) {}

    if (BackendConfig.initialized) {
      console.log('Backend bereits initialisiert');
      return;
    }

    console.log('Initialisiere Backend...');

    try {
      // Health Check (soft-fail)
      const healthy = await HttpManager.healthCheck();
      if (!healthy) console.warn('Backend Health Check failed - versuche trotzdem WebSocket');

      // WebSocket verbinden
      await WebSocketManager.initWebSocket(
        handlers.onMessage || function () {},
        handlers.onConnect || function () {},
        handlers.onDisconnect || function () {}
      );

      // LLM Modelle melden (falls Handler vorhanden)
      if (handlers.onLlmModels) {
        try {
          const models = await HttpManager.getLlmModels();
          handlers.onLlmModels(models);
        } catch (e) {
          console.warn('LLM Models laden fehlgeschlagen:', e.message);
        }
      }

      BackendConfig.initialized = true;
      console.log('Backend erfolgreich initialisiert');
    } catch (e) {
      console.error('Backend Initialisierung fehlgeschlagen:', e);
      // Nicht erneut werfen – UI bleibt funktionsfähig; Reconnect-Logik aktiv
      try {
        if (handlers.onDisconnect) handlers.onDisconnect(e);
      } catch (_) {}
      return false;
    }
  },

  /* --------------------------- Convenience-APIs --------------------------- */

  sendText(text) {
    return WebSocketManager.sendMessage({ type: 'text', content: text });
  },

  sendAudio(audioDataUrl) {
    return WebSocketManager.sendMessage({ type: 'audio', content: audioDataUrl });
  },

  ping() {
    return WebSocketManager.sendMessage({ type: 'ping', timestamp: Date.now() });
  },

  testTts(text) {
    return WebSocketManager.sendMessage({ type: 'tts_test', content: text || 'Test der Sprachsynthese' });
  },

  getStatus() {
    return WebSocketManager.getStatus();
  },

  shutdown() {
    WebSocketManager.close();
    BackendConfig.initialized = false;
  },

  async cleanup() {
    this.shutdown();
  },

  /* ------------------------------ Default-Handler ------------------------------ */

  defaultMessageHandler(data) {
    console.log('Backend Message:', data);
    if (window.App?.handleBackendMessage) {
      window.App.handleBackendMessage(data);
    }
  },

  defaultConnectHandler() {
    console.log('Backend Connected');
    if (window.App?.handleBackendConnected) {
      window.App.handleBackendConnected();
    }
  },

  defaultDisconnectHandler(event) {
    console.log('Backend Disconnected:', event?.code);
    if (window.App?.handleBackendDisconnected) {
      window.App.handleBackendDisconnected(event);
    }
  },

  defaultLlmModelsHandler(models) {
    console.log('LLM Models:', models);
    if (window.App?.handleLlmModels) {
      window.App.handleLlmModels(models);
    }
  }
};

/* ---------------------------- Globale Exporte ------------------------------- */

window.BackendUtils = BackendUtils;
window.Backend = Backend;

export default Backend;
