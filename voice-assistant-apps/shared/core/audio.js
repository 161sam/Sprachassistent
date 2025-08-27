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
 * Audio Konfiguration
 */
const AudioConfig = {
  // TTS Settings
  ttsVolume: 1.0,
  ttsSpeed: 1.0,
  crossfadeDuration: 100, // ms
  
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
      // Data URL Format sicherstellen
      let audioUrl = audioData;
      if (!audioData.startsWith('data:')) {
        // Base64 -> Data URL
        audioUrl = `data:audio/wav;base64,${audioData}`;
      }

      // Audio Element erstellen
      const audio = new Audio(audioUrl);
      audio.volume = options.volume || AudioConfig.ttsVolume;
      audio.playbackRate = options.speed || AudioConfig.ttsSpeed;

      // Promise für Playback Ende
      const playPromise = new Promise(function(resolve, reject) {
        audio.addEventListener('ended', resolve);
        audio.addEventListener('error', reject);
        audio.addEventListener('loadeddata', function() {
          console.log('TTS Audio geladen:', {
            duration: audio.duration,
            volume: audio.volume,
            playbackRate: audio.playbackRate
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
          autoGainControl: options.autoGainControl !== false
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
    if (AudioConfig.currentAudio) {
      AudioConfig.currentAudio.playbackRate = AudioConfig.ttsSpeed;
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