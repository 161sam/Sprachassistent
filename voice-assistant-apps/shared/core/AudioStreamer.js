/**
 * 🎵 AudioStreamer.js - Enhanced with Binary Audio Support
 *
 * High-performance audio streaming with real-time processing
 * Reduces latency from ~200ms to ~50ms through:
 * - Binary audio frames (new) + JSON base64 fallback
 * - Small chunk streaming (1024 bytes vs 4096 bytes)
 * - Non-blocking WebSocket operations
 * - VAD-based auto-stop detection
 * - Adaptive quality based on network conditions
 * - GPU-accelerated audio processing via WebAudio API
 */

// TODO: unify with VoiceAssistantCore.js to avoid duplicate streaming logic
//       (see TODO-Index.md: Frontend/Streaming)

let getAuthToken;
try {
    ({ getAuthToken } = require('./ws-utils'));
} catch (_) {
    if (typeof window !== 'undefined' && window.wsUtils) {
        getAuthToken = window.wsUtils.getAuthToken;
    }
}

class AudioStreamer {
    constructor(config = {}) {
        this.config = {
            // Tuned for low latency
            chunkSize: 1024,              // Smaller chunks = lower latency
            chunkIntervalMs: 50,          // 50ms intervals instead of 100ms
            sampleRate: 16000,            // for STT
            channels: 1,                  // Mono for efficiency
            bufferSize: 512,              // Small buffer for real-time processing
            
            // Binary audio support
            useBinaryFrames: true,        // NEW: Use binary WebSocket messages
            fallbackToJson: true,         // Fallback to base64 JSON if binary fails
            
            // VAD (Voice Activity Detection) settings
            vadEnabled: true,             // NEW: Enable VAD-based auto-stop
            vadThreshold: 0.01,           // RMS threshold for voice detection
            vadSilenceDuration: 1500,     // ms of silence before auto-stop
            vadWindowSize: 2048,          // samples for VAD analysis
            
            // WebSocket optimizations
            maxRetries: 5,
            retryDelay: 1000,
            pingInterval: 20000,
            
            // Quality settings
            adaptiveQuality: true,
            qualityThresholds: {
                excellent: 30,    // <30ms latency
                good: 100,        // <100ms latency  
                poor: 300         // >300ms latency
            },
            
            // Audio processing
            useWorklets: true,
            enableNoiseSupression: true,
            enableEchoCancellation: true,
            autoGainControl: true,
            
            // Performance monitoring
            enableInterimTranscripts: false,  // NEW: Real-time partial results
            metricsUrl: null,
            metricsInterval: 10000,
            ...config
        };
        
        this.isStreaming = false;
        this.audioContext = null;
        this.mediaStream = null;
        this.audioWorklet = null;
        this.websocket = null;
        this._currentStreamId = null;
        this.currentStreamId = null;
        
        // Binary audio support
        this.binaryModeSupported = false;
        this.audioFrameSequence = 0;
        
        // VAD state
        this.vadState = {
            isActive: false,
            silenceStartTime: null,
            rmsHistory: [],
            vadAnalyser: null
        };
        
        // Performance metrics
        this.metrics = {
            latency: {
                current: 0,
                average: 0,
                samples: []
            },
            audio: {
                chunksSent: 0,
                totalBytes: 0,
                droppedChunks: 0,
                binaryFrames: 0,
                jsonFrames: 0
            },
            connection: {
                connected: false,
                reconnectAttempts: 0,
                lastPing: 0,
                binarySupported: false
            },
            vad: {
                activations: 0,
                avgSilenceDuration: 0,
                falsePositives: 0
            }
        };
        
        if (this.config.metricsUrl) {
            setInterval(() => this.reportMetrics(), this.config.metricsInterval);
        }

        // Event handlers
        this.onConnected = null;
        this.onDisconnected = null;
        this.onResponse = null;
        this.onError = null;
        this.onMetricsUpdate = null;
        this.onInterimTranscript = null;  // NEW: For partial STT results
        this.onVadStateChange = null;     // NEW: For VAD feedback
        this.onTtsChunk = null;           // NEW: Handle staged TTS chunks
        this.onTtsSequenceEnd = null;     // NEW: Handle end of TTS sequence

        // Staged TTS playback
        this.playbackNode = null;
        this.playbackPort = null;
        this.playbackReady = false;
        
        this.init();
    }
    
    async init() {
        try {
            // Initialize WebAudio Context with optimized settings
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.config.sampleRate,
                latencyHint: 'interactive'  // for real-time
            });
            
            // Load audio worklet for GPU-accelerated processing
            if (this.config.useWorklets && this.audioContext.audioWorklet) {
                await this.loadAudioWorklet();
            }
            
            console.log('✅ AudioStreamer initialized with binary support');
        } catch (error) {
            console.error('❌ AudioStreamer initialization failed:', error);
            throw error;
        }
    }
    
    async loadAudioWorklet() {
        try {
            // Load the enhanced audio worklet processor with VAD support
            await this.audioContext.audioWorklet.addModule('workers/audio-streaming-worklet.js');
            console.log('✅ Enhanced audio worklet loaded');
        } catch (error) {
            console.warn('⚠️ Audio worklet not available, falling back to ScriptProcessor');
            this.config.useWorklets = false;
        }
    }

    async connect(wsUrl) {
        // Ensure a valid token is always appended
        const token = await getAuthToken();
        if (typeof wsUrl === 'string' && wsUrl.indexOf('token=') === -1) {
            wsUrl += (wsUrl.indexOf('?') > -1 ? '&' : '?') + 'token=' + encodeURIComponent(token);
        }

        return new Promise((resolve, reject) => {
            try {
                console.log("🔌 Connecting to", wsUrl);
                this.websocket = new WebSocket(wsUrl);
                
                // Set binary type for binary frame support
                this.websocket.binaryType = 'arraybuffer';

                const handleOpen = () => {
                    try {
                        this.metrics.connection.connected = true;
                        this.metrics.connection.reconnectAttempts = 0;

                        // Generate unique stream identifier
                        let streamId;
                        try {
                            streamId = globalThis.crypto?.randomUUID?.();
                        } catch (_) {}
                        if (!streamId) {
                            streamId = Math.random().toString(36).slice(2);
                        }
                        this.currentStreamId = streamId;
                        
                        // Enhanced handshake with binary capability info
                        this.websocket.send(JSON.stringify({
                            op: 'hello',
                            version: 2,  // Updated version for binary support
                            stream_id: streamId,
                            device: 'web',
                            capabilities: {
                                binaryAudio: this.config.useBinaryFrames,
                                vad: this.config.vadEnabled,
                                interimTranscripts: this.config.enableInterimTranscripts
                            }
                        }));
                        console.log('🔗 WebSocket connected with binary support');
                    } catch (e) {
                        console.warn('Handshake setup failed', e);
                    }
                };

                const handleMessage = (event) => {
                    try {
                        // Handle both binary and text messages
                        if (event.data instanceof ArrayBuffer) {
                            this.handleBinaryFrame(event.data);
                            return;
                        }
                        
                        const data = JSON.parse(event.data);
                        if (data.op === 'ready') {
                            // Check if server supports binary frames
                            this.binaryModeSupported = data.capabilities?.binaryAudio || false;
                            this.metrics.connection.binarySupported = this.binaryModeSupported;
                            
                            console.log(`📡 Binary mode: ${this.binaryModeSupported ? 'Supported' : 'Fallback to JSON'}`);
                            
                            // Switch to normal handler
                            this.websocket.removeEventListener('message', handleMessage);
                            this.websocket.onmessage = (ev) => this.handleWebSocketMessage(ev);
                            this.handleWebSocketMessage(event);
                            resolve();
                        } else {
                            this.handleWebSocketMessage(event);
                        }
                    } catch (e) {
                        console.error('Error parsing WebSocket message:', e);
                    }
                };

                this.websocket.addEventListener('open', handleOpen, { once: true });
                if (this.websocket.readyState === WebSocket.OPEN) {
                    handleOpen();
                }

                this.websocket.addEventListener('message', handleMessage);

                this.websocket.addEventListener('close', (ev) => {
                    this.metrics.connection.connected = false;
                    if (this.onDisconnected) this.onDisconnected(ev);
                    console.log(`❌ WebSocket disconnected (${ev.code} ${ev.reason || ''})`);
                    if (this.metrics.connection.reconnectAttempts < this.config.maxRetries) {
                        this.reconnect(wsUrl);
                    }
                });

                this.websocket.addEventListener('error', (error) => {
                    if (this.onError) this.onError(error);
                    console.error('🔥 WebSocket error:', error);
                    reject(error);
                });

            } catch (error) {
                reject(error);
            }
        });
    }
    
    async reconnect(wsUrl) {
        this.metrics.connection.reconnectAttempts++;
        let delay = this.config.retryDelay * Math.pow(2, this.metrics.connection.reconnectAttempts - 1);
        delay = Math.min(delay, 30000);
        console.log(`🔄 Reconnecting in ${delay}ms (attempt ${this.metrics.connection.reconnectAttempts})`);

        setTimeout(() => {
            this.connect(wsUrl);
        }, delay);
    }
    
    startPingMonitoring() {
        setInterval(() => {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                const pingTime = Date.now();
                this.metrics.connection.lastPing = pingTime;
                
                this.websocket.send(JSON.stringify({
                    type: 'ping',
                    timestamp: pingTime
                }));
            }
        }, this.config.pingInterval);
    }
    
    handleBinaryFrame(arrayBuffer) {
        if (!arrayBuffer) return;
        this._ensurePlayback().then(() => {
            if (this.playbackPort) {
                const bytes = new Uint8Array(arrayBuffer);
                let split = -1;
                for (let i = 1; i < bytes.length; i++) {
                    if (bytes[i - 1] === 10 && bytes[i] === 10) { // \n\n
                        split = i + 1;
                        break;
                    }
                }
                if (split > 0) {
                    const headerText = new TextDecoder('utf-8').decode(bytes.slice(0, split));
                    try {
                        const meta = JSON.parse(headerText.trim());
                        if (meta && meta.op === 'staged_tts_chunk') {
                            const sr = meta.sampleRate || 48000;
                            const f32 = new Float32Array(arrayBuffer, split);
                            this._enqueueFloat32(f32, sr);
                            if (this.onTtsChunk) this.onTtsChunk(meta);
                            return;
                        }
                    } catch (_) {
                        // ignore parse errors
                    }
                }
            }

            // Fallback: forward as generic binary response
            if (this.onResponse) {
                this.onResponse({
                    type: 'binary_audio_response',
                    data: arrayBuffer,
                    format: 'binary'
                });
            }
        });
    }

    async handleStagedChunkJSON(msg) {
        if (!msg || msg.op !== 'staged_tts_chunk') return;
        await this._ensurePlayback();
        const sr = msg.sampleRate || 48000;
        const fmt = (msg.format || 'f32').toLowerCase();
        if (fmt !== 'f32') return;
        const pcm = this._b64ToFloat32(msg.pcm);
        this._enqueueFloat32(pcm, sr);
        if (this.onTtsChunk) this.onTtsChunk(msg);
    }

    handleStagedEnd() {
        if (this.playbackPort) {
            this.playbackPort.postMessage({ type: 'flush' });
        }
        if (this.onTtsSequenceEnd) {
            this.onTtsSequenceEnd({ op: 'staged_tts_end' });
        }
    }

    async _ensurePlayback() {
        if (this.playbackReady) return;
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 48000 });
        }
        try {
            if (!this.playbackNode) {
                await this.audioContext.audioWorklet.addModule('workers/audio-streaming-worklet.js');
                this.playbackNode = new AudioWorkletNode(this.audioContext, 'audio-streaming-worklet');
                this.playbackPort = this.playbackNode.port;
                this.playbackNode.connect(this.audioContext.destination);
            }
            this.playbackReady = true;
            console.log('[AudioStreamer] playback ready');
        } catch (e) {
            console.warn('AudioWorklet init failed', e);
        }
    }

    _enqueueFloat32(f32, sampleRate) {
        if (!this.playbackPort) return;
        if (this.audioContext.sampleRate !== sampleRate) {
            this.playbackPort.postMessage({ type: 'config', sampleRate });
        }
        this.playbackPort.postMessage({ type: 'audio', format: 'f32', data: f32 }, [f32.buffer]);
    }

    _b64ToFloat32(b64) {
        const bin = atob(b64);
        const len = bin.length;
        const buf = new ArrayBuffer(len);
        const view = new Uint8Array(buf);
        for (let i = 0; i < len; i++) view[i] = bin.charCodeAt(i);
        return new Float32Array(buf);
    }
    
    handleWebSocketMessage(event) {
        try {
            // Binary messages handled separately
            if (event.data instanceof ArrayBuffer) {
                this.handleBinaryFrame(event.data);
                return;
            }
            
            const data = JSON.parse(event.data);
            
            if (data.op === 'ready') {
                // Server ready - start connection maintenance
                this.startPingMonitoring();
                try {
                    this.websocket.send(JSON.stringify({ type: 'start_audio_stream' }));
                } catch (e) {
                    console.warn('Failed to request audio stream', e);
                }
                if (this.onConnected) this.onConnected();
                return;
            }

            if (data.type === 'pong') {
                // Calculate latency
                const latency = Date.now() - data.client_timestamp;
                this.updateLatencyMetrics(latency);
                if (this.config.adaptiveQuality) this.adaptQualityBasedOnLatency(latency);
            } else if (data.type === 'audio_stream_started') {
                this.currentStreamId = data.stream_id;
            } else if (data.type === 'audio_stream_ended') {
                this.currentStreamId = null;
            } else if (data.type === 'interim_transcript') {
                // NEW: Handle partial STT results
                if (this.onInterimTranscript) this.onInterimTranscript(data);
            } else if (data.type === 'response' || data.type === 'audio_response') {
                if (this.onResponse) this.onResponse(data);
            } else if (data.type === 'tts_chunk') {
                if (this.onTtsChunk) this.onTtsChunk(data);
            } else if (data.type === 'tts_sequence_end') {
                if (this.onTtsSequenceEnd) this.onTtsSequenceEnd(data);
            }
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }
    
    updateLatencyMetrics(latency) {
        this.metrics.latency.current = latency;
        this.metrics.latency.samples.push(latency);
        
        // Keep only last 50 samples
        if (this.metrics.latency.samples.length > 50) {
            this.metrics.latency.samples.shift();
        }
        
        // Calculate average
        this.metrics.latency.average = this.metrics.latency.samples.reduce((a, b) => a + b, 0) / this.metrics.latency.samples.length;
        
        if (this.onMetricsUpdate) {
            this.onMetricsUpdate(this.metrics);
        }
    }

    reportMetrics() {
        try {
            if (!this.config.metricsUrl) return;
            const payload = JSON.stringify(this.metrics);
            if (navigator.sendBeacon) {
                navigator.sendBeacon(this.config.metricsUrl, payload);
            } else {
                fetch(this.config.metricsUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: payload
                });
            }
        } catch (err) {
            console.warn('Failed to report metrics', err);
        }
    }
    
    adaptQualityBasedOnLatency(latency) {
        const thresholds = this.config.qualityThresholds;
        
        if (latency > thresholds.poor) {
            // Poor connection - reduce quality
            this.config.chunkSize = Math.min(2048, this.config.chunkSize * 1.5);
            this.config.chunkIntervalMs = Math.min(200, this.config.chunkIntervalMs * 1.5);
        } else if (latency < thresholds.excellent) {
            // Excellent connection - increase quality
            this.config.chunkSize = Math.max(512, this.config.chunkSize * 0.8);
            this.config.chunkIntervalMs = Math.max(25, this.config.chunkIntervalMs * 0.8);
        }
        
        console.log(`📊 Quality adapted: ${latency}ms latency, chunk: ${this.config.chunkSize}, interval: ${this.config.chunkIntervalMs}ms`);
    }
    
    async startAudioStream() {
        try {
            // Request microphone access with optimized constraints
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: this.config.sampleRate,
                    channelCount: this.config.channels,
                    echoCancellation: this.config.enableEchoCancellation,
                    noiseSuppression: this.config.enableNoiseSupression,
                    autoGainControl: this.config.autoGainControl,
                    latency: 0.01,  // Request lowest possible latency
                    volume: 1.0
                }
            });
            
            // Create audio processing pipeline
            await this.setupAudioProcessing();
            
            // Stream beim Server anmelden
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({ 
                    type: 'start_audio_stream', 
                    timestamp: Date.now(),
                    config: {
                        binaryMode: this.binaryModeSupported && this.config.useBinaryFrames,
                        vadEnabled: this.config.vadEnabled,
                        interimTranscripts: this.config.enableInterimTranscripts
                    }
                }));
            }
            this.isStreaming = true;
            console.log('🎤 Enhanced audio streaming started');
            
        } catch (error) {
            console.error('❌ Failed to start audio stream:', error);
            throw error;
        }
    }
    
    async setupAudioProcessing() {
        const source = this.audioContext.createMediaStreamSource(this.mediaStream);
        
        // Setup VAD analyser if enabled
        if (this.config.vadEnabled) {
            this.setupVAD(source);
        }
        
        if (this.config.useWorklets && this.audioContext.audioWorklet) {
            // Use AudioWorklet for superior performance
            this.audioWorklet = new AudioWorkletNode(this.audioContext, 'audio-streaming-processor', {
                processorOptions: {
                    chunkSize: this.config.chunkSize,
                    vadEnabled: this.config.vadEnabled,
                    vadWindowSize: this.config.vadWindowSize
                }
            });
            
            this.audioWorklet.port.onmessage = (event) => {
                const { audioData, vadInfo } = event.data;
                
                // Process VAD information
                if (vadInfo && this.config.vadEnabled) {
                    this.processVAD(vadInfo);
                }
                
                this.sendAudioChunk(audioData);
            };
            
            source.connect(this.audioWorklet);
            
        } else {
            // Fallback to ScriptProcessorNode
            const scriptProcessor = this.audioContext.createScriptProcessor(this.config.bufferSize, 1, 1);
            
            scriptProcessor.onaudioprocess = (event) => {
                const inputBuffer = event.inputBuffer.getChannelData(0);
                
                // VAD processing for fallback mode
                if (this.config.vadEnabled) {
                    const rms = this.calculateRMS(inputBuffer);
                    this.processVAD({ rms, timestamp: Date.now() });
                }
                
                // Convert to Int16Array for transmission
                const int16Array = new Int16Array(inputBuffer.length);
                for (let i = 0; i < inputBuffer.length; i++) {
                    int16Array[i] = Math.max(-32768, Math.min(32767, inputBuffer[i] * 32767));
                }
                
                this.sendAudioChunk(int16Array.buffer);
            };
            
            source.connect(scriptProcessor);
            scriptProcessor.connect(this.audioContext.destination);
        }
    }
    
    setupVAD(source) {
        // Create analyser for VAD
        this.vadState.vadAnalyser = this.audioContext.createAnalyser();
        this.vadState.vadAnalyser.fftSize = this.config.vadWindowSize;
        source.connect(this.vadState.vadAnalyser);
    }
    
    calculateRMS(audioData) {
        let sum = 0;
        for (let i = 0; i < audioData.length; i++) {
            sum += audioData[i] * audioData[i];
        }
        return Math.sqrt(sum / audioData.length);
    }
    
    processVAD(vadInfo) {
        const { rms, timestamp } = vadInfo;
        const isVoiceActive = rms > this.config.vadThreshold;
        
        // Track RMS history for adaptive threshold
        this.vadState.rmsHistory.push(rms);
        if (this.vadState.rmsHistory.length > 100) {
            this.vadState.rmsHistory.shift();
        }
        
        // State machine for VAD
        if (isVoiceActive && !this.vadState.isActive) {
            // Voice started
            this.vadState.isActive = true;
            this.vadState.silenceStartTime = null;
            this.metrics.vad.activations++;
            
            if (this.onVadStateChange) {
                this.onVadStateChange({ active: true, rms, timestamp });
            }
            
        } else if (!isVoiceActive && this.vadState.isActive) {
            // Potential voice end - start silence timer
            if (!this.vadState.silenceStartTime) {
                this.vadState.silenceStartTime = timestamp;
            } else if (timestamp - this.vadState.silenceStartTime > this.config.vadSilenceDuration) {
                // Voice ended after sufficient silence
                this.vadState.isActive = false;
                this.vadState.silenceStartTime = null;
                
                if (this.onVadStateChange) {
                    this.onVadStateChange({ active: false, rms, timestamp });
                }
                
                // Auto-stop recording if enabled
                if (this.isStreaming) {
                    console.log('🤐 VAD detected end of speech, auto-stopping');
                    this.stopAudioStream();
                }
            }
        } else if (isVoiceActive && this.vadState.silenceStartTime) {
            // Voice resumed during silence period
            this.vadState.silenceStartTime = null;
        }
    }
    
    sendAudioChunk(audioData) {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            this.metrics.audio.droppedChunks++;
            return;
        }
        if (!this.currentStreamId) {
            this.metrics.audio.droppedChunks++;
            return;
        }
        
        try {
            // Try binary mode first if supported
            if (this.binaryModeSupported && this.config.useBinaryFrames) {
                this.sendBinaryAudioFrame(audioData);
            } else {
                this.sendJsonAudioFrame(audioData);
            }
            
            // Update metrics
            this.metrics.audio.chunksSent++;
            this.metrics.audio.totalBytes += audioData.byteLength;
            
        } catch (error) {
            console.error('Error sending audio chunk:', error);
            this.metrics.audio.droppedChunks++;
            
            // Fallback to JSON if binary fails
            if (this.binaryModeSupported && this.config.fallbackToJson) {
                console.warn('📦 Binary send failed, falling back to JSON');
                this.binaryModeSupported = false;
                this.sendJsonAudioFrame(audioData);
            }
        }
    }
    
    sendBinaryAudioFrame(audioData) {
        // Create binary frame: [stream_id_length][stream_id][sequence][timestamp][audio_data]
        const streamIdBytes = new TextEncoder().encode(this.currentStreamId);
        const headerSize = 4 + streamIdBytes.length + 4 + 8; // lengths + sequence + timestamp
        const frameBuffer = new ArrayBuffer(headerSize + audioData.byteLength);
        const view = new DataView(frameBuffer);
        
        let offset = 0;
        
        // Stream ID length (4 bytes)
        view.setUint32(offset, streamIdBytes.length, true);
        offset += 4;
        
        // Stream ID
        new Uint8Array(frameBuffer, offset, streamIdBytes.length).set(streamIdBytes);
        offset += streamIdBytes.length;
        
        // Sequence number (4 bytes)
        view.setUint32(offset, this.audioFrameSequence++, true);
        offset += 4;
        
        // Timestamp (8 bytes)
        view.setBigUint64(offset, BigInt(Date.now()), true);
        offset += 8;
        
        // Audio data
        new Uint8Array(frameBuffer, offset).set(new Uint8Array(audioData));
        
        // Send binary frame
        this.websocket.send(frameBuffer);
        this.metrics.audio.binaryFrames++;
    }
    
    sendJsonAudioFrame(audioData) {
        // Fallback to base64 JSON format
        const base64Audio = this.arrayBufferToBase64(audioData);
        
        const message = { 
            type: 'audio_chunk', 
            stream_id: this.currentStreamId,
            chunk: base64Audio,
            sequence: this.metrics.audio.chunksSent,
            timestamp: Date.now(),
            config: {
                sampleRate: this.config.sampleRate,
                channels: this.config.channels,
                format: 'int16'
            }
        };
        
        this.websocket.send(JSON.stringify(message));
        this.metrics.audio.jsonFrames++;
    }
    
    arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }
    
    async stopAudioStream() {
        this.isStreaming = false;
        
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        
        if (this.audioWorklet) {
            this.audioWorklet.disconnect();
            this.audioWorklet = null;
        }
        
        // Reset VAD state
        this.vadState = {
            isActive: false,
            silenceStartTime: null,
            rmsHistory: [],
            vadAnalyser: this.vadState.vadAnalyser // Keep analyser
        };
        
        // Send end stream message
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'end_audio_stream', 
                stream_id: this.currentStreamId, 
                timestamp: Date.now(),
                reason: 'manual_stop'
            }));
        }
        
        console.log('🛑 Enhanced audio streaming stopped');
    }
    
    // NEW: Settings update methods
    updateVADConfig(vadConfig) {
        Object.assign(this.config, vadConfig);
        console.log('🔊 VAD config updated:', vadConfig);
    }
    
    updateAudioConfig(audioConfig) {
        Object.assign(this.config, audioConfig);
        console.log('🎚️ Audio config updated:', audioConfig);
    }
    
    sendText(text) {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            throw new Error('WebSocket not connected');
        }
        
        this.websocket.send(JSON.stringify({
            type: 'text',
            content: text,
            timestamp: Date.now()
        }));
    }
    
    ping() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            const timestamp = Date.now();
            this.websocket.send(JSON.stringify({
                type: 'ping',
                timestamp: timestamp
            }));
            return timestamp;
        }
        return null;
    }
    
    getMetrics() {
        return {
            ...this.metrics,
            config: {
                chunkSize: this.config.chunkSize,
                chunkIntervalMs: this.config.chunkIntervalMs,
                adaptiveQuality: this.config.adaptiveQuality,
                binaryMode: this.binaryModeSupported,
                vadEnabled: this.config.vadEnabled
            }
        };
    }
    
    disconnect() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        if (this.isStreaming) {
            this.stopAudioStream();
        }
        
        this.metrics.connection.connected = false;
        this.binaryModeSupported = false;
    }
}

/**
 * 🤖 Enhanced Voice Assistant Core
 */
class VoiceAssistant {
    constructor(config = {}) {
        this.config = {
            wsUrl: 'ws://127.0.0.1:48232',
            chunkSize: 1024,
            chunkIntervalMs: 50,
            adaptiveQuality: true,
            enableNotifications: true,
            enableHaptics: 'vibrate' in navigator,

            // Enhanced features
            useBinaryFrames: true,
            vadEnabled: true,
            enableInterimTranscripts: false,
            quickstartPiper: true,
            chunkedPlayback: true,
            crossfadeDurationMs: 100,

            ...config
        };

        this.streamer = new AudioStreamer(this.config);
        this.isRecording = false;
        this.platform = this.detectPlatform();
        this.ttsSequences = new Map();
        this.currentTtsAudio = null;
        this.currentSequenceId = null;
        
        // UI elements (will be set externally)
        this.ui = {
            statusElement: null,
            responseElement: null,
            recordButton: null,
            metricsElement: null
        };
        
        this.setupEventHandlers();

        // Enhanced TTS cache with compression support
        this.ttsCache = new Map();
        this.loadTtsCache();
    }
    
    detectPlatform() {
        const userAgent = navigator.userAgent.toLowerCase();
        if (/mobile|android|iphone|ipad|ipod/.test(userAgent)) {
            return 'mobile';
        }
        return 'desktop';
    }
    
    setupEventHandlers() {
        // Connection events
        this.streamer.onConnected = () => {
            this.updateStatus('connected', '✅ Verbunden (Binary Mode)');
            if (this.config.enableNotifications) {
                const mode = this.streamer.binaryModeSupported ? 'Binary' : 'JSON';
                this.showNotification('success', 'Verbunden', `WebSocket-Verbindung hergestellt (${mode})`);
            }
        };
        
        this.streamer.onDisconnected = () => {
            this.updateStatus('disconnected', '❌ Getrennt');
            if (this.config.enableNotifications) {
                this.showNotification('error', 'Verbindung verloren', 'Versuche zu reconnecten...');
            }
        };
        
        this.streamer.onResponse = (data) => {
            this.handleResponse(data);
        };
        
        this.streamer.onError = (error) => {
            console.error('Voice Assistant Error:', error);
            if (this.config.enableNotifications) {
                this.showNotification('error', 'Fehler', error.message);
            }
        };
        
        this.streamer.onMetricsUpdate = (metrics) => {
            this.updateMetricsDisplay(metrics);
        };

        // NEW: Enhanced event handlers
        this.streamer.onInterimTranscript = (data) => {
            if (this.config.enableInterimTranscripts) {
                this.showInterimTranscript(data.transcript);
            }
        };

        this.streamer.onTtsChunk = (data) => {
            this.handleTtsChunk(data);
        };

        this.streamer.onTtsSequenceEnd = (data) => {
            this.handleTtsSequenceEnd(data);
        };

        this.streamer.onVadStateChange = (vadInfo) => {
            this.handleVadStateChange(vadInfo);
        };
    }
    
    async initialize() {
        try {
            await this.streamer.connect(this.config.wsUrl);
            this.updateStatus('connected', '✅ Bereit');
            return true;
        } catch (error) {
            this.updateStatus('error', '❌ Verbindung fehlgeschlagen');
            throw error;
        }
    }
    
    async startRecording() {
        if (this.isRecording) return;
        
        try {
            await this.streamer.startAudioStream();
            this.isRecording = true;
            
            const mode = this.streamer.binaryModeSupported ? 'Binary' : 'JSON';
            const vadStatus = this.config.vadEnabled ? 'VAD Ein' : 'VAD Aus';
            this.updateStatus('recording', `🎤 Aufnahme läuft... (${mode}, ${vadStatus})`);
            
            if (this.config.enableHaptics) {
                this.hapticFeedback([100]);
            }
            
        } catch (error) {
            this.updateStatus('error', '❌ Mikrofon-Fehler');
            throw error;
        }
    }
    
    async stopRecording() {
        if (!this.isRecording) return;
        
        await this.streamer.stopAudioStream();
        this.isRecording = false;
        
        this.updateStatus('processing', '⏳ Verarbeitung...');
        
        if (this.config.enableHaptics) {
            this.hapticFeedback([50, 50, 50]);
        }
    }
    
    async sendText(text) {
        if (!text.trim()) return;
        
        try {
            this.streamer.sendText(text);
            this.updateStatus('processing', '⏳ Verarbeitung...');
        } catch (error) {
            this.updateStatus('error', '❌ Senden fehlgeschlagen');
            throw error;
        }
    }
    
    handleResponse(data) {
        this.updateStatus('connected', '✅ Bereit');

        if (this.ui.responseElement) {
            this.displayResponse(data.content || data.transcription);
        }

        // Play TTS audio if available or cached
        if (data.audio || this.ttsCache.has(data.content)) {
            this.playTTSAudio(data.content, data.audio);
        }
    }

    handleTtsChunk(data) {
        if (data.text) {
            this.displayResponse(data.text);
        }

        if (!this.config.chunkedPlayback) {
            this.playTTSAudio(data.text || '', data.audio);
            return;
        }

        const id = data.sequence_id || 'default';

        if (!this.ttsSequences.has(id)) {
            this.ttsSequences.set(id, { chunks: [], index: 0, ended: false, currentAudio: null });
        }

        const seq = this.ttsSequences.get(id);
        const src = data.audio.startsWith('data:') ? data.audio : `data:audio/wav;base64,${data.audio}`;
        const audio = new Audio(src);
        audio.preload = 'auto';
        audio.load();
        seq.chunks[data.index] = audio;

        if (!this.currentSequenceId) this.currentSequenceId = id;

        if (
            id === this.currentSequenceId &&
            !seq.currentAudio &&
            data.index === seq.index &&
            (this.config.quickstartPiper || data.engine !== 'piper')
        ) {
            this.playNextTtsChunk();
        }

        if (this.ui.statusElement && typeof data.index === 'number' && typeof data.total === 'number') {
            this.updateStatus('playing', `🔊 ${data.index + 1}/${data.total}`);
        }
    }

    handleTtsSequenceEnd(data) {
        const id = data.sequence_id || this.currentSequenceId;
        const seq = this.ttsSequences.get(id);
        if (!seq) return;
        seq.ended = true;
        if (id === this.currentSequenceId && !seq.currentAudio) {
            this.playNextTtsChunk();
        }
    }

    playNextTtsChunk() {
        if (!this.currentSequenceId) {
            const first = this.ttsSequences.keys().next();
            if (first.done) return;
            this.currentSequenceId = first.value;
        }

        const seq = this.ttsSequences.get(this.currentSequenceId);
        if (!seq) {
            this.currentSequenceId = null;
            return;
        }

        const next = seq.chunks[seq.index];
        if (!next) return;

        seq.index++;
        next.volume = 0;

        next.addEventListener('loadedmetadata', () => {
            const upcoming = seq.chunks[seq.index];
            if (upcoming) upcoming.load();
            const wait = Math.max((next.duration * 1000) - this.config.crossfadeDurationMs, 0);
            setTimeout(() => this.playNextTtsChunk(), wait);
        });

        next.addEventListener('ended', () => {
            seq.currentAudio = null;
            if (seq.ended && seq.index >= seq.chunks.length) {
                this.ttsSequences.delete(this.currentSequenceId);
                this.currentSequenceId = null;
                this.playNextTtsChunk();
            }
        });

        next.play().then(() => {
            this.crossfadeAudios(this.currentTtsAudio, next);
            this.currentTtsAudio = next;
            seq.currentAudio = next;
        }).catch(err => {
            console.warn('TTS chunk playback failed:', err);
        });
    }

    crossfadeAudios(prev, next) {
        const duration = this.config.crossfadeDurationMs;
        const steps = 10;
        const stepTime = duration / steps;
        let step = 0;
        if (prev) prev.volume = 1;
        next.volume = 0;

        const interval = setInterval(() => {
            step++;
            const t = step / steps;
            if (prev) prev.volume = 1 - t;
            next.volume = t;
            if (step >= steps) {
                clearInterval(interval);
                if (prev) prev.pause();
            }
        }, stepTime);
    }

    updatePlaybackSettings(settings) {
        this.config = { ...this.config, ...settings };
    }
    
    // NEW: Enhanced methods
    showInterimTranscript(transcript) {
        if (this.ui.responseElement) {
            // Show partial transcript with different styling
            const interimElement = this.ui.responseElement.querySelector('.interim-transcript') || 
                                  document.createElement('div');
            interimElement.className = 'interim-transcript';
            interimElement.style.opacity = '0.6';
            interimElement.style.fontStyle = 'italic';
            interimElement.textContent = `🎤 ${transcript}...`;
            
            if (!this.ui.responseElement.contains(interimElement)) {
                this.ui.responseElement.appendChild(interimElement);
            }
        }
    }
    
    handleVadStateChange(vadInfo) {
        if (vadInfo.active) {
            console.log('🗣️ Voice detected');
            if (this.ui.statusElement) {
                this.ui.statusElement.style.borderColor = '#10b981';
            }
        } else {
            console.log('🤐 Silence detected');
            if (this.ui.statusElement) {
                this.ui.statusElement.style.borderColor = '';
            }
        }
    }
    
    // Enhanced settings update methods
    updateVADSettings(vadSettings) {
        this.streamer.updateVADConfig(vadSettings);
        this.config = { ...this.config, ...vadSettings };
    }
    
    updateAudioSettings(audioSettings) {
        this.streamer.updateAudioConfig(audioSettings);
        this.config = { ...this.config, ...audioSettings };
    }
    
    displayResponse(content) {
        if (!this.ui.responseElement) return;
        
        // Clear interim transcripts
        const interim = this.ui.responseElement.querySelector('.interim-transcript');
        if (interim) interim.remove();
        
        // Matrix rain effect for response text
        this.matrixRainEffect(this.ui.responseElement, content);
    }
    
    matrixRainEffect(element, text) {
        const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
        let iteration = 0;
        
        const interval = setInterval(() => {
            element.textContent = text
                .split('')
                .map((char, index) => {
                    if (index < iteration) {
                        return char;
                    }
                    return letters[Math.floor(Math.random() * letters.length)];
                })
                .join('');
                
            if (iteration >= text.length) {
                clearInterval(interval);
                element.textContent = text;
            }
            iteration += 1;
        }, 30);
    }
    
    loadTtsCache() {
        if (typeof localStorage === 'undefined') return;
        try {
            const stored = JSON.parse(localStorage.getItem('ttsCache') || '{}');
            for (const [k, v] of Object.entries(stored)) {
                this.ttsCache.set(k, v);
            }
        } catch (e) {
            console.warn('Failed to load TTS cache', e);
        }
    }

    saveTtsCache() {
        if (typeof localStorage === 'undefined') return;
        try {
            localStorage.setItem('ttsCache', JSON.stringify(Object.fromEntries(this.ttsCache)));
        } catch (e) {
            console.warn('Failed to save TTS cache', e);
        }
    }

    playTTSAudio(text, audioData) {
        let src = this.ttsCache.get(text);
        if (!src && audioData) {
            src = audioData.startsWith('data:') ? audioData : `data:audio/wav;base64,${audioData}`;
            this.ttsCache.set(text, src);
            this.saveTtsCache();
        }
        if (src) {
            const audio = new Audio(src);
            audio.play().catch(error => {
                console.warn('TTS audio playback failed:', error);
            });
        }
    }
    
    updateStatus(type, message) {
        if (this.ui.statusElement) {
            this.ui.statusElement.textContent = message;
            this.ui.statusElement.className = `status-text ${type}`;
        }
    }
    
    updateMetricsDisplay(metrics) {
        if (!this.ui.metricsElement) return;
        
        const binaryRatio = metrics.audio.binaryFrames / (metrics.audio.binaryFrames + metrics.audio.jsonFrames) * 100;
        
        this.ui.metricsElement.innerHTML = `
            <div>Latenz: ${metrics.latency.average.toFixed(0)}ms</div>
            <div>Chunks: ${metrics.audio.chunksSent}</div>
            <div>Bytes: ${(metrics.audio.totalBytes / 1024).toFixed(1)}KB</div>
            <div>Binary: ${binaryRatio.toFixed(0)}%</div>
            <div>VAD: ${metrics.vad.activations}</div>
            <div>Quality: ${this.getConnectionQuality(metrics.latency.average)}</div>
        `;
    }
    
    getConnectionQuality(latency) {
        if (latency < 50) return '🟢 Exzellent';
        if (latency < 100) return '🟡 Gut';
        if (latency < 300) return '🟠 Mäßig';
        return '🔴 Schlecht';
    }
    
    hapticFeedback(pattern) {
        if (this.config.enableHaptics && 'vibrate' in navigator) {
            navigator.vibrate(pattern);
        }
    }
    
    showNotification(type, title, message) {
        // This should be implemented by the UI layer
        console.log(`[${type.toUpperCase()}] ${title}: ${message}`);
    }
    
    getMetrics() {
        return this.streamer.getMetrics();
    }
    
    disconnect() {
        if (this.isRecording) {
            this.stopRecording();
        }
        this.streamer.disconnect();
    }
}

// Enhanced Voice Assistant Client (Compatibility Layer)
class VoiceAssistantClient extends VoiceAssistant {
    constructor(config = {}) {
        super(config);
        
        // Add backward compatibility for existing code
        this.settings = {
            responseNebel: true,
            avatarAnimation: true,
            notifications: true,
            useBinaryAudio: true,
            vadEnabled: true,
            ...config
        };
    }
    
    // Backward compatibility methods
    async connect() {
        return this.initialize();
    }
    
    async startStreaming() {
        return this.startRecording();
    }
    
    async stopStreaming() {
        return this.stopRecording();
    }
    
    sendMessage(message) {
        if (message.type === 'text') {
            return this.sendText(message.content);
        }
        // Handle other message types as needed
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        AudioStreamer,
        VoiceAssistant,
        VoiceAssistantClient
    };
}

// Global access for script tags
window.AudioStreamer = AudioStreamer;
window.VoiceAssistant = VoiceAssistant;
window.VoiceAssistantClient = VoiceAssistantClient;
