/**
 * Voice Assistant Core with Audio Streaming & Mobile-First Design
 * Designed for low latency, real-time audio streaming, and mobile UX
 */

class VoiceAssistantCore {
  constructor() {
    this.isInitialized = false;
    this.platform = this.detectPlatform();
    this.ws = null;
    this.audioContext = null;
    this.mediaRecorder = null;
    this.audioWorklet = null;
    this.currentStream = null;
    this.streamId = null;

    this.llmModels = [];
    this.currentLlmModel = null;
    
    // Performance monitoring
    this.metrics = {
      latency: [],
      audioChunks: 0,
      reconnections: 0,
      errors: 0
    };
    
    // Audio streaming configuration
    this.audioConfig = {
      sampleRate: 16000, // for speech
      channels: 1,
      chunkSize: 4096,
      bufferSize: 2048,
      codec: 'opus'
    };
    
    // Settings with mobile optimizations
    this.settings = {
      // Core features
      responseNebel: true,
      avatarAnimation: true,
      animationSpeed: 1.0,
      
      // Audio settings
      audioStreaming: true,
      realTimeTranscription: false,
      voiceActivationDetection: true,
      noiseSuppression: true,
      echoCancellation: true,
      autoGainControl: true,
      
      // Mobile-specific
      hapticFeedback: this.platform === 'mobile',
      backgroundMode: false,
      lowPowerMode: false,
      adaptiveQuality: true,
      
      // UI/UX
      notifications: true,
      reducedMotion: false,
      glassOpacity: 0.05,
      touchOptimizations: this.platform === 'mobile',
      gestureSupport: this.platform === 'mobile',
      
      // Network
      autoReconnect: true,
      connectionTimeout: 3000,
      maxRetries: 3,
      
      // Performance
      cacheResponses: true,
      preloadAudio: false,
      optimizeForBattery: this.platform === 'mobile',
      
      // Visual effects
        nebelColors: {
          primary: '#6366f1',
          secondary: '#10b981',
          accent: '#f59e0b'
        },
        sttModel: 'Faster-Whisper',
        ttsEngine: 'Zonos',
        wsHost: '127.0.0.1',
        wsPort: 48231
      };

    this.cache = new Map();
    this.gestureHandler = null;
    this.serviceWorker = null;
    
    console.log(`🚀 Voice Assistant Core initialized (Platform: ${this.platform})`);
  }

  detectPlatform() {
    // Platform detection
    if (typeof cordova !== 'undefined') return 'mobile';
    if (window.electronAPI?.isElectron) return 'desktop';
    
    const userAgent = navigator.userAgent.toLowerCase();
    const isMobile = /android|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent);
    const isTablet = /ipad|android(?!.*mobile)/i.test(userAgent);
    
    if (isMobile) return 'mobile';
    if (isTablet) return 'tablet';
    if ('serviceWorker' in navigator) return 'pwa';
    return 'web';
  }

  async initialize() {
    if (this.isInitialized) return;

    console.log('🔧 Initializing Voice Assistant...');

    try {
      // Initialize audio context early
      await this.initializeAudioContext();
      
      // Platform-specific initialization
      await this.initializePlatformFeatures();
      
      // Network initialization
      await this.initializeWebSocket();
      
      // Service Worker for PWA features
      await this.initializeServiceWorker();
      
      // UI initialization
      this.setupEventListeners();
      this.initializeGestures();
      this.loadSettings();
      this.applySettings();
      
      // Start performance monitoring
      this.startPerformanceMonitoring();
      
      this.isInitialized = true;
      console.log('✅ Voice Assistant successfully initialized');
      
      this.showNotification('success', 'System Ready', 'Voice Assistant optimized and ready');
      
    } catch (error) {
      console.error('❌ Initialization error:', error);
      this.showNotification('error', 'Initialization Failed', error.message);
      this.metrics.errors++;
    }
  }

  async initializeAudioContext() {
    try {
      // Create optimized audio context
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: this.audioConfig.sampleRate,
        latencyHint: 'interactive'
      });

      // Resume context if suspended (mobile requirement)
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      // Load audio worklet for real-time processing
      if (this.audioContext.audioWorklet) {
        try {
          await this.audioContext.audioWorklet.addModule('/audio-worklet-processor.js');
        } catch (e) {
          console.warn('Audio worklet not available, falling back to script processor');
        }
      }

      console.log('🎵 Audio context initialized:', {
        sampleRate: this.audioContext.sampleRate,
        state: this.audioContext.state,
        latency: this.audioContext.outputLatency || 'unknown'
      });

    } catch (error) {
      console.error('Audio context initialization failed:', error);
      throw new Error('Audio system not available');
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
      case 'pwa':
        await this.initializePWAFeatures();
        break;
      default:
        await this.initializeWebFeatures();
    }
  }

  async initializeMobileFeatures() {
    console.log('📱 Initializing mobile optimizations...');
    
    // Haptic feedback support
    if ('vibrate' in navigator) {
      this.hapticFeedback = (pattern = 50) => navigator.vibrate(pattern);
    }
    
    // Screen wake lock for recording
    if ('wakeLock' in navigator) {
      this.wakeLock = null;
    }
    
    // Mobile-specific audio settings
    this.audioConfig.bufferSize = 1024; // Smaller for lower latency
    this.settings.adaptiveQuality = true;
    this.settings.lowPowerMode = navigator.getBattery ? (await navigator.getBattery()).charging === false : false;
    
    // Optimize for mobile performance
    this.settings.animationSpeed = 1.5; // Faster animations
    this.settings.cacheResponses = true;
  }

  async initializeDesktopFeatures() {
    console.log('🖥️ Initializing desktop features...');
    
    // Desktop-specific optimizations
    this.audioConfig.bufferSize = 4096; // Larger buffer for stability
    this.settings.realTimeTranscription = true;
    this.settings.preloadAudio = true;
  }

  async initializePWAFeatures() {
    console.log('📱🌐 Initializing PWA features...');
    
    // PWA-specific features
    this.settings.backgroundMode = true;
    this.settings.cacheResponses = true;
    
    // Install prompt handling
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      this.deferredPrompt = e;
      this.showInstallPrompt();
    });
  }

  async initializeServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js');
        this.serviceWorker = registration;
        console.log('🔄 Service Worker registered:', registration);
        
        // Listen for messages from service worker
        navigator.serviceWorker.addEventListener('message', (event) => {
          this.handleServiceWorkerMessage(event.data);
        });
        
      } catch (error) {
        console.warn('Service Worker registration failed:', error);
      }
    }
  }

  async initializeWebSocket() {
    // Retrieve token and append it to the WebSocket URL so the backend can
    // authenticate the connection before the handshake completes.
    const token = await this.getAuthToken();
    const wsUrl = `${this.getWebSocketURL()}?token=${encodeURIComponent(token)}`;
    console.log('🔌 Connecting to:', wsUrl);

    try {
      this.ws = new WebSocket(wsUrl);
      this.ws.binaryType = 'arraybuffer';

      const handleOpen = () => {
        try {
          console.log('✅ WebSocket connected');

          // Send initial handshake expected by the server
          const streamId = (globalThis.crypto?.randomUUID?.())
            || Math.random().toString(36).slice(2);
          this.ws.send(JSON.stringify({
            op: 'hello',
            version: 1,
            stream_id: streamId,
            device: this.platform,
            stt_model: localStorage.getItem('sttModel') || this.settings.sttModel,
            tts_engine: localStorage.getItem('ttsEngine') || this.settings.ttsEngine
          }));

          // Reset reconnection attempts after a successful connection
          this.metrics.reconnections = 0;
        } catch (e) {
          console.warn('Failed to complete WebSocket handshake', e);
        }
      };

      this.ws.onopen = handleOpen;
      // It's possible for extremely fast connections to reach OPEN before the
      // onopen handler is registered. Trigger manually in that case.
      if (this.ws.readyState === WebSocket.OPEN) {
        handleOpen();
      }

      this.ws.onmessage = (event) => {
        this.handleWebSocketMessage(event);
      };

      this.ws.onclose = (event) => {
        console.log('🔌 WebSocket closed:', event.code, event.reason);
        this.updateConnectionStatus('disconnected', '❌ Disconnected');
        
        if (this.settings.autoReconnect && event.code !== 1000) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('🔌 WebSocket error:', error);
        this.updateConnectionStatus('error', '❌ Connection Error');
        this.metrics.errors++;
      };

    } catch (error) {
      console.error('WebSocket initialization failed:', error);
      throw new Error('Cannot connect to voice server');
    }
  }

  async authenticate() {
    // Generate or retrieve auth token
    const token = await this.getAuthToken();
    
    this.sendMessage({
      type: 'auth',
      token: token,
      platform: this.platform,
      capabilities: this.getClientCapabilities()
    });
  }

  scheduleReconnect() {
    if (this.metrics.reconnections >= this.settings.maxRetries) {
      console.warn('Max reconnect attempts reached');
      return;
    }
    this.metrics.reconnections++;
    const delay = Math.min(
      this.settings.connectionTimeout * Math.pow(2, this.metrics.reconnections - 1),
      30000
    );
    console.log(`🔄 Reconnecting in ${delay}ms (attempt ${this.metrics.reconnections}/${this.settings.maxRetries})`);
    setTimeout(() => this.initializeWebSocket(), delay);
  }

  getClientCapabilities() {
    return {
      audioStreaming: !!this.audioContext,
      audioWorklet: !!(this.audioContext && this.audioContext.audioWorklet),
      webrtc: !!(window.RTCPeerConnection),
      mediaRecorder: !!window.MediaRecorder,
      wakeLock: !!navigator.wakeLock,
      vibrate: !!navigator.vibrate,
      serviceWorker: !!navigator.serviceWorker
    };
  }

  updateConnectionStatus(type, message) {
    if (typeof window !== 'undefined' && typeof window.updateStatus === 'function') {
      window.updateStatus(type, message);
    } else {
      console.log(`Status: ${type} - ${message}`);
    }
  }

  handleConnected(data) {
    this.updateConnectionStatus('connected', '✅ Connected');
    this.authenticate();
    this.sendMessage({ type: 'get_llm_models' });
  }

  handleWebSocketMessage(event) {
    try {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'connected':
          this.handleConnected(data);
          break;
        case 'response':
      this.handleResponse(data);
      break;
        case 'audio_ready':
          this.streamId = data.stream_id;
          break;
        case 'llm_models':
          this.handleLlmModels(data);
          break;
        case 'llm_model_switched':
          this.handleLlmModelSwitched(data);
          break;
        case 'audio_error':
          this.handleAudioError(data);
          break;
        case 'pong':
          this.handlePong(data);
          break;
        case 'error':
      this.handleError(data);
      break;
    }
  } catch (error) {
    console.error('Message parsing error:', error);
  }
}

  handleLlmModels(data) {
    this.llmModels = data.models || [];
    this.currentLlmModel = data.current || null;
    if (typeof window.renderModelDropdown === 'function') {
      window.renderModelDropdown(this.llmModels, this.currentLlmModel);
    }
  }

  handleLlmModelSwitched(data) {
    if (data.ok) {
      this.currentLlmModel = data.current;
    }
    if (typeof window.updateLlmModel === 'function') {
      window.updateLlmModel(data.current, data.ok);
    }
  }

  switchLlmModel(model) {
    this.sendMessage({ type: 'switch_llm_model', model });
  }

  // Audio Recording with Real-time Streaming
  async startRecording() {
    if (this.isRecording) return;

    try {
      // Request wake lock on mobile
      if (this.wakeLock && 'wakeLock' in navigator) {
        this.wakeLock = await navigator.wakeLock.request('screen');
      }

      // Get media stream with optimized constraints
      const constraints = {
        audio: {
          sampleRate: this.audioConfig.sampleRate,
          channelCount: this.audioConfig.channels,
          echoCancellation: this.settings.echoCancellation,
          noiseSuppression: this.settings.noiseSuppression,
          autoGainControl: this.settings.autoGainControl,
          latency: 0.01 // Request low latency
        }
      };

      this.currentStream = await navigator.mediaDevices.getUserMedia(constraints);
      
      if (this.settings.audioStreaming) {
        await this.startStreamingRecording();
      } else {
        await this.startBufferedRecording();
      }

      this.isRecording = true;
      this.updateRecordingUI(true);
      this.startRecordingTimer();
      
      // Haptic feedback
      if (this.hapticFeedback) {
        this.hapticFeedback([50, 50, 50]);
      }

      this.showNotification('success', 'Recording Started', 'Speak now...');

    } catch (error) {
      console.error('Recording start failed:', error);
      this.showNotification('error', 'Recording Failed', error.message);
      this.metrics.errors++;
    }
  }

  async startStreamingRecording() {
    // Initialize audio streaming
    this.sendMessage({ type: 'audio_start' });
    
    // Create media recorder for streaming
    this.mediaRecorder = new MediaRecorder(this.currentStream, {
      mimeType: 'audio/webm;codecs=opus',
      audioBitsPerSecond: 32000 // bitrate
    });

    let chunkCounter = 0;
    
    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0 && this.streamId) {
        // Convert to base64 and stream
        const reader = new FileReader();
        reader.onload = () => {
          const base64 = reader.result.split(',')[1];
          this.sendMessage({
            type: 'audio_chunk',
            stream_id: this.streamId,
            chunk: base64,
            sequence: chunkCounter++
          });
          this.metrics.audioChunks++;
        };
        reader.readAsDataURL(event.data);
      }
    };

    this.mediaRecorder.onstop = () => {
      this.sendMessage({
        type: 'audio_end',
        stream_id: this.streamId
      });
    };

    // Start recording with small time slices for streaming
    this.mediaRecorder.start(100); // 100ms chunks for low latency
  }

  async startBufferedRecording() {
    // Fallback to buffered recording
    this.mediaRecorder = new MediaRecorder(this.currentStream);
    this.audioChunks = [];

    this.mediaRecorder.ondataavailable = (event) => {
      this.audioChunks.push(event.data);
    };

    this.mediaRecorder.onstop = () => {
      const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
      this.processAudioBlob(audioBlob);
    };

    this.mediaRecorder.start();
  }

  async stopRecording() {
    if (!this.isRecording) return;

    try {
      if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
        this.mediaRecorder.stop();
      }

      if (this.currentStream) {
        this.currentStream.getTracks().forEach(track => track.stop());
        this.currentStream = null;
      }

      // Release wake lock
      if (this.wakeLock) {
        await this.wakeLock.release();
        this.wakeLock = null;
      }

      this.isRecording = false;
      this.updateRecordingUI(false);
      this.stopRecordingTimer();

      // Haptic feedback
      if (this.hapticFeedback) {
        this.hapticFeedback(100);
      }

      this.showNotification('success', 'Recording Stopped', 'Processing...');

    } catch (error) {
      console.error('Recording stop failed:', error);
      this.metrics.errors++;
    }
  }

  // Gesture support for mobile
  initializeGestures() {
    if (!this.settings.gestureSupport) return;

    let startY = 0;
    let startTime = 0;
    let isGesturing = false;

    const handleTouchStart = (e) => {
      if (e.touches.length === 1) {
        startY = e.touches[0].clientY;
        startTime = Date.now();
        isGesturing = true;
      }
    };

    const handleTouchMove = (e) => {
      if (!isGesturing || e.touches.length !== 1) return;
      
      const currentY = e.touches[0].clientY;
      const deltaY = startY - currentY;
      const deltaTime = Date.now() - startTime;
      
      // Swipe up gesture to start recording
      if (deltaY > 100 && deltaTime < 500) {
        e.preventDefault();
        if (!this.isRecording) {
          this.startRecording();
        }
        isGesturing = false;
      }
      
      // Swipe down gesture to stop recording
      if (deltaY < -100 && deltaTime < 500) {
        e.preventDefault();
        if (this.isRecording) {
          this.stopRecording();
        }
        isGesturing = false;
      }
    };

    const handleTouchEnd = () => {
      isGesturing = false;
    };

    document.addEventListener('touchstart', handleTouchStart, { passive: false });
    document.addEventListener('touchmove', handleTouchMove, { passive: false });
    document.addEventListener('touchend', handleTouchEnd);

    // Long press for continuous recording
    let longPressTimer;
    const voiceButton = document.getElementById('voiceBtn');
    
    if (voiceButton) {
      voiceButton.addEventListener('touchstart', (e) => {
        longPressTimer = setTimeout(() => {
          if (!this.isRecording) {
            this.startRecording();
            this.hapticFeedback?.(200);
          }
        }, 500);
      });

      voiceButton.addEventListener('touchend', (e) => {
        clearTimeout(longPressTimer);
        if (this.isRecording) {
          this.stopRecording();
        }
      });
    }
  }

  // Performance monitoring
  startPerformanceMonitoring() {
    setInterval(() => {
      // Monitor connection latency
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        const start = Date.now();
        this.sendMessage({ type: 'ping', timestamp: start });
      }
      
      // Monitor audio performance
      if (this.audioContext) {
        const cpuUsage = this.audioContext.outputLatency || 0;
        if (cpuUsage > 0.1) { // High latency detected
          this.optimizeForPerformance();
        }
      }
      
      // Battery optimization
      if (this.settings.optimizeForBattery && this.platform === 'mobile') {
        this.checkBatteryStatus();
      }
    }, 5000);
  }

  handlePong(data) {
    const latency = Date.now() - data.timestamp;
    this.metrics.latency.push(latency);
    
    // Keep only last 10 measurements
    if (this.metrics.latency.length > 10) {
      this.metrics.latency.shift();
    }
    
    // Adaptive quality based on latency
    if (this.settings.adaptiveQuality) {
      const avgLatency = this.metrics.latency.reduce((a, b) => a + b, 0) / this.metrics.latency.length;
      this.adjustQualityForLatency(avgLatency);
    }
  }

  adjustQualityForLatency(latency) {
    if (latency > 1000) { // High latency
      this.audioConfig.chunkSize = 2048; // Smaller chunks
      this.settings.realTimeTranscription = false;
      this.settings.animationSpeed = 2.0; // Faster animations
    } else if (latency < 200) { // Low latency
      this.audioConfig.chunkSize = 8192; // Larger chunks
      this.settings.realTimeTranscription = true;
      this.settings.animationSpeed = 1.0; // Normal animations
    }
  }

  async checkBatteryStatus() {
    if ('getBattery' in navigator) {
      try {
        const battery = await navigator.getBattery();
        
        if (battery.level < 0.2 && !battery.charging) {
          // Enable power saving mode
          this.settings.lowPowerMode = true;
          this.settings.animationSpeed = 3.0;
          this.settings.cacheResponses = true;
          this.settings.preloadAudio = false;
          
          this.showNotification('warning', 'Low Battery', 'Power saving mode enabled');
        }
      } catch (error) {
        console.warn('Battery status not available');
      }
    }
  }

  // Caching with IndexedDB
  async cacheResponse(key, response) {
    if (!this.settings.cacheResponses) return;
    
    try {
      // Use IndexedDB for persistent caching
      if ('indexedDB' in window) {
        // Implementation would go here
        this.cache.set(key, response);
      } else {
        this.cache.set(key, response);
      }
    } catch (error) {
      console.warn('Caching failed:', error);
    }
  }

  async getCachedResponse(key) {
    if (!this.settings.cacheResponses) return null;
    return this.cache.get(key);
  }

  // Notification system with mobile optimizations
  showNotification(type, title, message, options = {}) {
    if (!this.settings.notifications) return;

    // Native notifications for mobile/PWA
    if (this.platform === 'mobile' || this.platform === 'pwa') {
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, {
          body: message,
          icon: '/icons/icon-192x192.png',
          badge: '/icons/badge-72x72.png',
          vibrate: [200, 100, 200],
          ...options
        });
        return;
      }
    }

    // Fallback to web UI notification
    this.showWebNotification(type, title, message);
    
    // Haptic feedback for mobile
    if (this.hapticFeedback && type === 'error') {
      this.hapticFeedback([100, 100, 100]);
    }
  }

  // Utility methods
  sendMessage(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  getWebSocketURL() {
    const host = localStorage.getItem('wsHost') || this.settings.wsHost;
    const port = localStorage.getItem('wsPort') || this.settings.wsPort;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${host}:${port}`;
  }

  async getAuthToken() {
    // Generate or retrieve JWT token.  The token is also stored under
    // "wsToken" so other components (e.g. AudioStreamer) can reuse
    // it when establishing their own WebSocket connections.
    // Prefer an existing token from localStorage (either a previously stored
    // voice_auth_token or wsToken).  Fallback to the development token
    // "devsecret" so that desktop and web clients behave consistently during
    // local testing.
    const token =
      localStorage.getItem('voice_auth_token') ||
      localStorage.getItem('wsToken') ||
      'devsecret';

    // Expose the token under "wsToken" so other components (e.g. the
    // AudioStreamer) can append it automatically to their WebSocket URLs.
    try { localStorage.setItem('wsToken', token); } catch (_) {}
    return token;
  }

  getMetrics() {
    const avgLatency = this.metrics.latency.length > 0 
      ? this.metrics.latency.reduce((a, b) => a + b, 0) / this.metrics.latency.length 
      : 0;

    return {
      platform: this.platform,
      latency: {
        current: this.metrics.latency[this.metrics.latency.length - 1] || 0,
        average: avgLatency,
        samples: this.metrics.latency.length
      },
      audio: {
        chunksStreamed: this.metrics.audioChunks,
        sampleRate: this.audioConfig.sampleRate,
        bufferSize: this.audioConfig.bufferSize
      },
      connection: {
        reconnections: this.metrics.reconnections,
        errors: this.metrics.errors
      },
      performance: {
        lowPowerMode: this.settings.lowPowerMode,
        adaptiveQuality: this.settings.adaptiveQuality
      }
    };
  }

  // Cleanup
  async destroy() {
    if (this.ws) {
      this.ws.close();
    }
    
    if (this.currentStream) {
      this.currentStream.getTracks().forEach(track => track.stop());
    }
    
    if (this.audioContext) {
      await this.audioContext.close();
    }
    
    if (this.wakeLock) {
      await this.wakeLock.release();
    }
    
    console.log('🧹 Voice Assistant Core destroyed');
  }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = VoiceAssistantCore;
}

// Global initialization
if (typeof window !== 'undefined') {
  window.VoiceAssistantCore = VoiceAssistantCore;
}
