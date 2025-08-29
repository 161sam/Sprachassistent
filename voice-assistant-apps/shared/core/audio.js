/**
 * Audio Management - TTS Playback & Recording
 * 
 * Verwaltet Audio-Ein/Ausgabe für den Sprachassistenten
 * - TTS Audio Playback mit Crossfading
 * - Mikrofon-Aufnahme mit VAD
 * - Audio Visualization
 * - WebAudio API Integration
 */

import { DOMHelpers } from './dom-helpers.js';

/**
 * Helpers to comply with CSP: convert data/base64 → Blob URL (blob:)
 */
function toBlobUrl(input, mime = 'audio/wav') {
  try {
    if (!input) return '';
    if (typeof input !== 'string') return '';
    if (input.startsWith('blob:')) return input;
    let byteArray = null;
    if (input.startsWith('data:')) {
      // data:[<mediatype>][;base64],<data>
      const comma = input.indexOf(',');
      const header = input.slice(0, comma);
      const b64 = input.slice(comma + 1);
      const isB64 = /;base64/i.test(header);
      const contentType = (header.match(/^data:([^;]+)/i)?.[1]) || mime;
      if (isB64) {
        const bin = atob(b64);
        const len = bin.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) bytes[i] = bin.charCodeAt(i);
        byteArray = new Blob([bytes], { type: contentType });
      } else {
        // URL-encoded
        const decoded = decodeURIComponent(b64);
        byteArray = new Blob([decoded], { type: contentType });
      }
    } else {
      // Assume raw base64 WAV
      const bin = atob(input);
      const len = bin.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) bytes[i] = bin.charCodeAt(i);
      byteArray = new Blob([bytes], { type: mime });
    }
    const url = URL.createObjectURL(byteArray);
    return url;
  } catch (e) {
    console.warn('toBlobUrl failed', e);
    return '';
  }
}

/**
 * Audio Konfiguration
 */
const AudioConfig = {
  // TTS Settings
  ttsVolume: 1.0,
  ttsSpeed: 1.0,
  crossfadeDuration: 60, // ms
  
  // Recording Settings
  sampleRate: 16000,
  channels: 1,
  bufferSize: 4096,
  
  // VAD Settings
  vadThreshold: 0.01,
  vadEnabled: true,
  
  // Audio Context
  audioContext: null,
  
  // Recording State
  mediaRecorder: null,
  recordingStream: null,
  isRecording: false,
  recordingStartTime: null,
  
  // Playback State
  currentAudio: null,
  audioQueue: [],
  // Chunked TTS sequences
  ttsSequences: new Map(),
  currentSequenceId: null,
  currentTtsAudio: null,
  
  // Visualization
  voiceAnalyzer: null,
  voiceCanvas: null,
  voiceCanvasContext: null,
  animationId: null
};

/**
 * Audio Context Manager
 */
export const AudioContextManager = {
  /**
   * AudioContext initialisieren
   * @returns {Promise<AudioContext>}
   */
  async initAudioContext() {
    if (AudioConfig.audioContext && AudioConfig.audioContext.state !== 'closed') {
      return AudioConfig.audioContext;
    }

    try {
      // AudioContext erstellen
      AudioConfig.audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: AudioConfig.sampleRate,
        latencyHint: 'interactive'
      });

      // Context aktivieren (mobile requirement)
      if (AudioConfig.audioContext.state === 'suspended') {
        await AudioConfig.audioContext.resume();
      }

      console.log('AudioContext initialisiert:', {
        sampleRate: AudioConfig.audioContext.sampleRate,
        state: AudioConfig.audioContext.state
      });

      return AudioConfig.audioContext;
    } catch (error) {
      console.error('AudioContext Initialisierung fehlgeschlagen:', error);
      throw error;
    }
  },

  /**
   * AudioContext Status
   * @returns {Object}
   */
  getStatus() {
    return {
      available: !!AudioConfig.audioContext,
      state: AudioConfig.audioContext ? AudioConfig.audioContext.state : 'none',
      sampleRate: AudioConfig.audioContext ? AudioConfig.audioContext.sampleRate : 0
    };
  }
};

/**
 * TTS Audio Player
 */
export const TTSPlayer = {
  /**
   * Audio aus Base64 oder Data URL spielen
   * @param {string} audioData - Base64 oder Data URL
   * @param {Object} options - Playback Optionen
   * @returns {Promise<void>}
   */
  async playAudio(audioData, options = {}) {
    if (!audioData) {
      console.warn('Keine Audio-Daten zum Abspielen');
      return;
    }

    try {
      // Ensure blob: URL (CSP-friendly)
      const audioUrl = toBlobUrl(audioData, 'audio/wav');
      if (!audioUrl) throw new Error('Ungültige Audiodaten');

      // Audio Element erstellen
      const audio = new Audio(audioUrl);
      audio.volume = options.volume || AudioConfig.ttsVolume;
      // TTS-Geschwindigkeit wird ausschließlich im Backend angewandt.
      // Player manipuliert keine Abspielgeschwindigkeit, Pitch bleibt stabil.
      try {
        audio.preservesPitch = true;
        audio.mozPreservesPitch = true;
        audio.webkitPreservesPitch = true;
      } catch (_) {}

      // Promise für Playback Ende
      const playPromise = new Promise(function(resolve, reject) {
        audio.addEventListener('ended', resolve);
        audio.addEventListener('error', reject);
        audio.addEventListener('loadeddata', function() {
          console.log('TTS Audio geladen:', {
            duration: audio.duration,
            volume: audio.volume,
            playbackRate: 1.0
          });
        });
      });

      // Crossfade mit aktuellem Audio
      if (AudioConfig.currentAudio && !AudioConfig.currentAudio.ended) {
        await TTSPlayer.crossfadeAudios(AudioConfig.currentAudio, audio);
      } else {
        await audio.play();
      }

      AudioConfig.currentAudio = audio;
      audio.addEventListener('ended', function () { try { URL.revokeObjectURL(audioUrl); } catch (_) {} });
      await playPromise;

    } catch (error) {
      console.error('TTS Audio Playback Fehler:', error);
      throw error;
    }
  },

  /**
   * Crossfade zwischen zwei Audio-Elementen
   * @param {HTMLAudioElement} oldAudio 
   * @param {HTMLAudioElement} newAudio 
   * @returns {Promise<void>}
   */
  async crossfadeAudios(oldAudio, newAudio) {
    const duration = AudioConfig.crossfadeDuration;
    const steps = 10;
    const stepTime = duration / steps;

    // Neues Audio starten (stumm)
    newAudio.volume = 0;
    await newAudio.play();

    // Fade-Prozess
    return new Promise(function(resolve) {
      let step = 0;
      const interval = setInterval(function() {
        step++;
        const progress = step / steps;
        
        // Volume anpassen
        if (oldAudio && !oldAudio.ended) {
          oldAudio.volume = Math.max(0, (1 - progress) * AudioConfig.ttsVolume);
        }
        newAudio.volume = Math.min(AudioConfig.ttsVolume, progress * AudioConfig.ttsVolume);

        // Fertig?
        if (step >= steps) {
          clearInterval(interval);
          if (oldAudio && !oldAudio.ended) {
            oldAudio.pause();
          }
          resolve();
        }
      }, stepTime);
    });
  },

  /**
   * Aktuelles Audio stoppen
   */
  stopCurrentAudio() {
    if (AudioConfig.currentAudio && !AudioConfig.currentAudio.ended) {
      AudioConfig.currentAudio.pause();
      AudioConfig.currentAudio.currentTime = 0;
    }
    AudioConfig.currentAudio = null;
  },

  /**
   * Audio Queue verwalten
   * @param {string} audioData 
   * @param {Object} options 
   */
  async queueAudio(audioData, options = {}) {
    AudioConfig.audioQueue.push({ audioData, options });
    
    // Erste Audio in Queue abspielen
    if (AudioConfig.audioQueue.length === 1) {
      await TTSPlayer.processQueue();
    }
  },

  /**
   * Audio Queue abarbeiten
   */
  async processQueue() {
    while (AudioConfig.audioQueue.length > 0) {
      const { audioData, options } = AudioConfig.audioQueue.shift();
      try {
        await TTSPlayer.playAudio(audioData, options);
      } catch (error) {
        console.error('Queue Audio Fehler:', error);
      }
    }
  }
};

/**
 * Audio Recording Manager
 */
export const RecordingManager = {
  /**
   * Aufnahme starten
   * @param {Object} options - Aufnahme-Optionen
   * @returns {Promise<void>}
   */
  async startRecording(options = {}) {
    if (AudioConfig.isRecording) {
      console.warn('Aufnahme läuft bereits');
      return;
    }

    try {
      // AudioContext initialisieren
      await AudioContextManager.initAudioContext();

      // Mikrofonzugriff anfordern
      const constraints = {
        audio: {
          sampleRate: AudioConfig.sampleRate,
          channelCount: AudioConfig.channels,
          echoCancellation: options.echoCancellation !== false,
          noiseSuppression: options.noiseSuppression !== false,
          autoGainControl: options.autoGainControl !== false,
          ...(options.deviceId ? { deviceId: { exact: options.deviceId } } : {})
        }
      };

      AudioConfig.recordingStream = await navigator.mediaDevices.getUserMedia(constraints);

      // MediaRecorder initialisieren
      AudioConfig.mediaRecorder = new MediaRecorder(AudioConfig.recordingStream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      const audioChunks = [];

      AudioConfig.mediaRecorder.ondataavailable = function(event) {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      AudioConfig.mediaRecorder.onstop = async function() {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        
        // Blob zu Data URL konvertieren
        const reader = new FileReader();
        reader.onloadend = function() {
          if (options.onAudioReady) {
            options.onAudioReady(reader.result);
          }
        };
        reader.readAsDataURL(audioBlob);

        // Stream beenden
        RecordingManager.cleanupRecording();
      };

      // Voice Visualization initialisieren
      if (options.enableVisualization !== false) {
        VoiceVisualizer.start(AudioConfig.recordingStream);
      }

      // Aufnahme starten
      AudioConfig.mediaRecorder.start();
      AudioConfig.isRecording = true;
      AudioConfig.recordingStartTime = Date.now();

      console.log('Audio-Aufnahme gestartet');

    } catch (error) {
      console.error('Recording Start Fehler:', error);
      RecordingManager.cleanupRecording();
      throw error;
    }
  },

  /**
   * Aufnahme stoppen
   * @returns {Promise<void>}
   */
  async stopRecording() {
    if (!AudioConfig.isRecording) {
      console.warn('Keine aktive Aufnahme');
      return;
    }

    try {
      if (AudioConfig.mediaRecorder && AudioConfig.mediaRecorder.state === 'recording') {
        AudioConfig.mediaRecorder.stop();
      }

      VoiceVisualizer.stop();
      AudioConfig.isRecording = false;
      
      const duration = Date.now() - AudioConfig.recordingStartTime;
      console.log('Audio-Aufnahme gestoppt, Dauer:', duration + 'ms');

    } catch (error) {
      console.error('Recording Stop Fehler:', error);
      throw error;
    }
  },

  /**
   * Recording Cleanup
   */
  cleanupRecording() {
    if (AudioConfig.recordingStream) {
      AudioConfig.recordingStream.getTracks().forEach(function(track) {
        track.stop();
      });
      AudioConfig.recordingStream = null;
    }

    AudioConfig.mediaRecorder = null;
    AudioConfig.isRecording = false;
    AudioConfig.recordingStartTime = null;
  },

  /**
   * Recording Status
   * @returns {Object}
   */
  getRecordingStatus() {
    return {
      isRecording: AudioConfig.isRecording,
      startTime: AudioConfig.recordingStartTime,
      duration: AudioConfig.recordingStartTime ? Date.now() - AudioConfig.recordingStartTime : 0,
      state: AudioConfig.mediaRecorder ? AudioConfig.mediaRecorder.state : 'inactive'
    };
  }
};

/**
 * Voice Visualizer für Recording Feedback
 */
export const VoiceVisualizer = {
  /**
   * Visualization initialisieren
   */
  init() {
    AudioConfig.voiceCanvas = DOMHelpers.$('#voiceCanvas');
    if (AudioConfig.voiceCanvas) {
      AudioConfig.voiceCanvasContext = AudioConfig.voiceCanvas.getContext('2d');
    }
  },

  /**
   * Visualization starten
   * @param {MediaStream} stream 
   */
  start(stream) {
    if (!AudioConfig.voiceCanvas || !AudioConfig.audioContext) {
      return;
    }

    try {
      // Analyzer erstellen
      AudioConfig.voiceAnalyzer = AudioConfig.audioContext.createAnalyser();
      AudioConfig.voiceAnalyzer.fftSize = 256;
      AudioConfig.voiceAnalyzer.smoothingTimeConstant = 0.8;

      // Stream mit Analyzer verbinden
      const source = AudioConfig.audioContext.createMediaStreamSource(stream);
      source.connect(AudioConfig.voiceAnalyzer);

      // Canvas aktivieren
      DOMHelpers.toggleClass(AudioConfig.voiceCanvas, 'active', true);

      // Animation starten
      VoiceVisualizer.animate();

    } catch (error) {
      console.error('Voice Visualizer Start Fehler:', error);
    }
  },

  /**
   * Animation Frame
   */
  animate() {
    if (!AudioConfig.voiceAnalyzer || !AudioConfig.voiceCanvasContext) {
      return;
    }

    const dataArray = new Uint8Array(AudioConfig.voiceAnalyzer.frequencyBinCount);
    AudioConfig.voiceAnalyzer.getByteFrequencyData(dataArray);

    VoiceVisualizer.draw(dataArray);
    
    AudioConfig.animationId = requestAnimationFrame(function() {
      VoiceVisualizer.animate();
    });
  },

  /**
   * Spektrum zeichnen
   * @param {Uint8Array} dataArray 
   */
  draw(dataArray) {
    const canvas = AudioConfig.voiceCanvas;
    const ctx = AudioConfig.voiceCanvasContext;
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) - 20;

    // Canvas leeren
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Spektrum als Kreis zeichnen
    const barCount = dataArray.length / 2;
    const angleStep = (2 * Math.PI) / barCount;

    for (let i = 0; i < barCount; i++) {
      const angle = i * angleStep;
      const barHeight = (dataArray[i] / 255) * 60;

      const x1 = centerX + Math.cos(angle) * radius;
      const y1 = centerY + Math.sin(angle) * radius;
      const x2 = centerX + Math.cos(angle) * (radius + barHeight);
      const y2 = centerY + Math.sin(angle) * (radius + barHeight);

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = `hsl(${(i / barCount) * 360}, 70%, 60%)`;
      ctx.lineWidth = 3;
      ctx.stroke();
    }
  },

  /**
   * Visualization stoppen
   */
  stop() {
    if (AudioConfig.animationId) {
      cancelAnimationFrame(AudioConfig.animationId);
      AudioConfig.animationId = null;
    }

    if (AudioConfig.voiceCanvas) {
      DOMHelpers.toggleClass(AudioConfig.voiceCanvas, 'active', false);
    }

    VoiceVisualizer.clear();
  },

  /**
   * Canvas leeren
   */
  clear() {
    if (AudioConfig.voiceCanvasContext && AudioConfig.voiceCanvas) {
      AudioConfig.voiceCanvasContext.clearRect(0, 0, AudioConfig.voiceCanvas.width, AudioConfig.voiceCanvas.height);
    }
  }
};

/**
 * Audio Settings Manager
 */
export const AudioSettings = {
  /**
   * TTS Volume setzen
   * @param {number} volume - 0.0 bis 1.0
   */
  setTtsVolume(volume) {
    AudioConfig.ttsVolume = Math.max(0, Math.min(1, volume));
    if (AudioConfig.currentAudio) {
      AudioConfig.currentAudio.volume = AudioConfig.ttsVolume;
    }
  },

  /**
   * TTS Speed setzen
   * @param {number} speed - 0.5 bis 2.0
   */
  setTtsSpeed(speed) {
    AudioConfig.ttsSpeed = Math.max(0.5, Math.min(2, speed));
    // Keine lokale Änderung der Abspielgeschwindigkeit – nur Volume anpassen
    if (AudioConfig.currentAudio) {
      try {
        AudioConfig.currentAudio.preservesPitch = true;
        AudioConfig.currentAudio.mozPreservesPitch = true;
        AudioConfig.currentAudio.webkitPreservesPitch = true;
      } catch (_) {}
    }
  },
  setTtsVolume(vol) {
    const v = Math.max(0.0, Math.min(2.0, parseFloat(vol)));
    AudioConfig.ttsVolume = isFinite(v) ? v : 1.0;
    if (AudioConfig.currentAudio) {
      AudioConfig.currentAudio.volume = Math.min(1.0, AudioConfig.ttsVolume);
    }
  },

  /**
   * Crossfade Duration setzen
   * @param {number} duration - Millisekunden
   */
  setCrossfadeDuration(duration) {
    AudioConfig.crossfadeDuration = Math.max(0, duration);
  },

  /**
   * VAD Threshold setzen
   * @param {number} threshold - 0.001 bis 0.1
   */
  setVadThreshold(threshold) {
    AudioConfig.vadThreshold = Math.max(0.001, Math.min(0.1, threshold));
  },

  /**
   * Aktuelle Settings
   * @returns {Object}
   */
  getSettings() {
    return {
      ttsVolume: AudioConfig.ttsVolume,
      ttsSpeed: AudioConfig.ttsSpeed,
      crossfadeDuration: AudioConfig.crossfadeDuration,
      vadThreshold: AudioConfig.vadThreshold,
      vadEnabled: AudioConfig.vadEnabled,
      sampleRate: AudioConfig.sampleRate
    };
  }
};

/**
 * Hauptklasse Audio Manager
 */
export const AudioManager = {

  async initialize() { return this.init(); },
  /**
   * Audio System initialisieren
   * @returns {Promise<void>}
   */
  async init() {
    try {
      console.log('Audio Manager initialisieren...');

      // AudioContext initialisieren
      await AudioContextManager.initAudioContext();

      // Voice Visualizer initialisieren
      VoiceVisualizer.init();

      console.log('Audio Manager bereit');
    } catch (error) {
      console.error('Audio Manager Init Fehler:', error);
      throw error;
    }
  },

  /**
   * TTS Audio abspielen
   * @param {string} audioData 
   * @param {Object} options 
   */
  async playTts(audioData, options = {}) {
    return TTSPlayer.playAudio(audioData, options);
  },

  /**
   * Aufnahme starten
   * @param {Object} options 
   */
  async startRecording(options = {}) {
    return RecordingManager.startRecording(options);
  },

  /**
   * Aufnahme stoppen
   */
  async stopRecording() {
    return RecordingManager.stopRecording();
  },

  /**
   * Recording Status
   */
  getRecordingStatus() {
    return RecordingManager.getRecordingStatus();
  },

  /**
   * Audio stoppen
   */
  stopAudio() {
    TTSPlayer.stopCurrentAudio();
  },

  setTtsVolume(vol) {
    const v = Math.max(0.0, Math.min(2.0, parseFloat(vol)));
    AudioConfig.ttsVolume = isFinite(v) ? v : 1.0;
    if (AudioConfig.currentAudio) {
      AudioConfig.currentAudio.volume = Math.min(1.0, AudioConfig.ttsVolume);
    }
  },

  /**
   * Queue a TTS chunk for staged playback with crossfade.
   * Expected data shape: { sequence_id, index, total, engine, audio }
   */
  addTtsChunk(data) {
    if (!data || typeof data.index !== 'number') return;
    const id = data.sequence_id || 'default';
    if (!AudioConfig.ttsSequences.has(id)) {
      AudioConfig.ttsSequences.set(id, { chunks: [], index: 0, ended: false, currentAudio: null });
    }
    const seq = AudioConfig.ttsSequences.get(id);
    const src = toBlobUrl(data.audio || '', 'audio/wav');
    const audio = new Audio(src);
    try {
      audio.preservesPitch = true;
      audio.mozPreservesPitch = true;
      audio.webkitPreservesPitch = true;
    } catch (_) {}
    audio.preload = 'auto';
    audio.load();
    seq.chunks[data.index] = audio;

    if (!AudioConfig.currentSequenceId) AudioConfig.currentSequenceId = id;
    if (id === AudioConfig.currentSequenceId && !seq.currentAudio && data.index === seq.index) {
      this._playNextTtsChunk();
    }
  },

  endTtsSequence(data) {
    const id = (data && data.sequence_id) || AudioConfig.currentSequenceId;
    const seq = id ? AudioConfig.ttsSequences.get(id) : null;
    if (!seq) return;
    seq.ended = true;
    if (id === AudioConfig.currentSequenceId && !seq.currentAudio) {
      this._playNextTtsChunk();
    }
  },

  _playNextTtsChunk() {
    if (!AudioConfig.currentSequenceId) {
      const first = AudioConfig.ttsSequences.keys().next();
      if (first.done) return;
      AudioConfig.currentSequenceId = first.value;
    }
    const seq = AudioConfig.ttsSequences.get(AudioConfig.currentSequenceId);
    if (!seq) { AudioConfig.currentSequenceId = null; return; }
    const next = seq.chunks[seq.index];
    if (!next) return;
    seq.index++;
    next.volume = 0;

    next.addEventListener('loadedmetadata', () => {
      const upcoming = seq.chunks[seq.index];
      if (upcoming) upcoming.load();
      const wait = Math.max((next.duration * 1000) - AudioConfig.crossfadeDuration, 0);
      setTimeout(() => this._playNextTtsChunk(), wait);
    });
    next.addEventListener('ended', () => {
      seq.currentAudio = null;
      if (seq.ended && seq.index >= seq.chunks.length) {
        AudioConfig.ttsSequences.delete(AudioConfig.currentSequenceId);
        AudioConfig.currentSequenceId = null;
        this._playNextTtsChunk();
      }
    });

    next.play().then(() => {
      TTSPlayer.crossfadeAudios(AudioConfig.currentTtsAudio, next);
      AudioConfig.currentTtsAudio = next;
      seq.currentAudio = next;
      try { next.addEventListener('ended', () => { try { URL.revokeObjectURL(next.src); } catch(_){} }); } catch(_){}
    }).catch((err) => {
      console.warn('TTS chunk playback failed:', err);
    });
  },

  /**
   * Settings
   */
  getSettings() {
    return AudioSettings.getSettings();
  },

  /**
   * Cleanup
   */
  cleanup() {
    TTSPlayer.stopCurrentAudio();
    RecordingManager.cleanupRecording();
    VoiceVisualizer.stop();
    
    if (AudioConfig.audioContext) {
      AudioConfig.audioContext.close();
      AudioConfig.audioContext = null;
    }
  }
};

// Globale Verfügbarkeit
window.AudioManager = AudioManager;
window.AudioSettings = AudioSettings;

export default AudioManager;
