/**
 * Optimized Frontend Audio Streaming Client
 * Complementary to the optimized backend for minimal latency
 * Features:
 * - Real-time audio streaming with small chunks
 * - Automatic reconnection with exponential backoff
 * - Performance monitoring
 * - Adaptive quality based on network conditions
 */

class OptimizedAudioStreamer {
    constructor(config = {}) {
        this.config = {
            // Optimized for low latency
            chunkSize: 1024,           // Small chunks for real-time streaming
            chunkIntervalMs: 50,       // Send chunk every 50ms
            sampleRate: 16000,         // Match backend config
            channels: 1,
            bufferSize: 512,           // Small buffer for low latency
            
            // WebSocket config
            wsUrl: config.wsUrl || 'ws://localhost:8123',
            reconnectInterval: 1000,
            maxReconnectAttempts: 5,
            
            // Performance monitoring
            enableMetrics: true,
            adaptiveQuality: true,
            
            ...config
        };
        
        this.ws = null;
        this.mediaRecorder = null;
        this.audioStream = null;
        this.currentStreamId = null;
        this.isStreaming = false;
        this.isConnected = false;
        
        // Performance metrics
        this.metrics = {
            latency: [],
            chunksSent: 0,
            chunksDropped: 0,
            reconnections: 0,
            totalBytes: 0
        };
        
        // Reconnection state
        this.reconnectAttempts = 0;
        this.reconnectTimer = null;
        
        // Audio processing
        this.audioContext = null;
        this.audioWorklet = null;
        this.chunkSequence = 0;
        
        // Event callbacks
        this.onConnected = null;
        this.onDisconnected = null;
        this.onResponse = null;
        this.onError = null;
        this.onMetrics = null;
        
        console.log('🎙️ OptimizedAudioStreamer initialized');
    }
    
    async initialize() {
        try {
            // Initialize audio context with optimized settings
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.config.sampleRate,
                latencyHint: 'interactive'  // Request lowest latency
            });
            
            // Resume context if suspended (mobile requirement)
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }
            
            // Try to load audio worklet for real-time processing
            try {
                await this.audioContext.audioWorklet.addModule('/audio-streaming-worklet.js');
                console.log('✅ Audio worklet loaded for real-time processing');
            } catch (e) {
                console.warn('⚠️ Audio worklet not available, using MediaRecorder fallback');
            }
            
            console.log('🎵 Audio context initialized:', {
                sampleRate: this.audioContext.sampleRate,
                state: this.audioContext.state,
                baseLatency: this.audioContext.baseLatency || 'unknown',
                outputLatency: this.audioContext.outputLatency || 'unknown'
            });
            
            return true;
        } catch (error) {
            console.error('❌ Audio initialization failed:', error);
            throw new Error('Audio system not available');
        }
    }
    
    async connect() {
        if (this.isConnected || this.ws) {
            return;
        }
        
        try {
            console.log(`🔌 Connecting to ${this.config.wsUrl}`);
            
            this.ws = new WebSocket(this.config.wsUrl);
            this.ws.binaryType = 'arraybuffer';
            
            // Set up event handlers
            this.ws.onopen = this._handleOpen.bind(this);
            this.ws.onmessage = this._handleMessage.bind(this);
            this.ws.onclose = this._handleClose.bind(this);
            this.ws.onerror = this._handleError.bind(this);
            
        } catch (error) {
            console.error('❌ WebSocket connection failed:', error);
            this._scheduleReconnect();
        }
    }
    
    disconnect() {
        this.isConnected = false;
        
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        
        if (this.isStreaming) {
            this.stopStreaming();
        }
        
        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
            this.ws = null;
        }
        
        console.log('🔌 Disconnected from server');
    }
    
    async startStreaming() {
        if (this.isStreaming || !this.isConnected) {
            return false;
        }
        
        try {
            console.log('🎤 Starting audio streaming...');
            
            // Get media stream with optimized constraints
            const constraints = {
                audio: {
                    sampleRate: this.config.sampleRate,
                    channelCount: this.config.channels,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    latency: 0.01,  // Request lowest possible latency
                    googEchoCancellation: true,
                    googNoiseSuppression: true,
                    googAutoGainControl: true,
                    googHighpassFilter: true
                }
            };
            
            this.audioStream = await navigator.mediaDevices.getUserMedia(constraints);
            
            // Start audio stream with server
            this._sendMessage({
                type: 'start_audio_stream',
                config: {
                    sampleRate: this.config.sampleRate,
                    channels: this.config.channels,
                    chunkSize: this.config.chunkSize
                }
            });
            
            // Use audio worklet if available, otherwise fallback to MediaRecorder
            if (this.audioContext.audioWorklet) {
                await this._startWorkletStreaming();
            } else {
                await this._startMediaRecorderStreaming();
            }
            
            this.isStreaming = true;
            this.chunkSequence = 0;
            
            console.log('✅ Audio streaming started');
            return true;
            
        } catch (error) {
            console.error('❌ Failed to start streaming:', error);
            this._callCallback('onError', { type: 'streaming_start_failed', error });
            return false;
        }
    }
    
    async stopStreaming() {
        if (!this.isStreaming) {
            return;
        }
        
        console.log('🛑 Stopping audio streaming...');
        
        this.isStreaming = false;
        
        // Stop MediaRecorder if active
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
        }
        
        // Stop audio worklet if active
        if (this.audioWorklet) {
            this.audioWorklet.disconnect();
            this.audioWorklet = null;
        }
        
        // Stop audio stream
        if (this.audioStream) {
            this.audioStream.getTracks().forEach(track => track.stop());
            this.audioStream = null;
        }
        
        // End stream with server
        if (this.currentStreamId) {
            this._sendMessage({
                type: 'end_audio_stream',
                stream_id: this.currentStreamId
            });
        }
        
        console.log('✅ Audio streaming stopped');
    }
    
    async _startWorkletStreaming() {
        console.log('🔧 Using AudioWorklet for real-time streaming');
        
        // Create audio worklet node for real-time processing
        this.audioWorklet = new AudioWorkletNode(this.audioContext, 'audio-streaming-processor', {
            processorOptions: {
                chunkSize: this.config.chunkSize
            }
        });
        
        // Handle processed audio chunks
        this.audioWorklet.port.onmessage = (event) => {
            if (this.isStreaming && this.currentStreamId) {
                const audioChunk = event.data.audioData;
                this._sendAudioChunk(audioChunk);
            }
        };
        
        // Connect audio stream to worklet
        const source = this.audioContext.createMediaStreamSource(this.audioStream);
        source.connect(this.audioWorklet);
        this.audioWorklet.connect(this.audioContext.destination);
    }
    
    async _startMediaRecorderStreaming() {
        console.log('🔧 Using MediaRecorder for streaming (fallback)');
        
        // Use MediaRecorder with optimized settings
        const options = {
            mimeType: 'audio/webm;codecs=opus',
            audioBitsPerSecond: 32000  // Optimized bitrate
        };
        
        this.mediaRecorder = new MediaRecorder(this.audioStream, options);
        
        this.mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0 && this.isStreaming && this.currentStreamId) {
                // Convert to ArrayBuffer and send
                const reader = new FileReader();
                reader.onload = () => {
                    const arrayBuffer = reader.result;
                    this._sendAudioChunk(new Uint8Array(arrayBuffer));
                };
                reader.readAsArrayBuffer(event.data);
            }
        };
        
        this.mediaRecorder.onerror = (error) => {
            console.error('MediaRecorder error:', error);
            this._callCallback('onError', { type: 'media_recorder_error', error });
        };
        
        // Start recording with small time slices for low latency
        this.mediaRecorder.start(this.config.chunkIntervalMs);
    }
    
    _sendAudioChunk(audioData) {
        if (!this.isStreaming || !this.currentStreamId || !this.isConnected) {
            return;
        }
        
        try {
            // Convert to base64 for WebSocket transmission
            const base64 = this._arrayBufferToBase64(audioData);
            
            this._sendMessage({
                type: 'audio_chunk',
                stream_id: this.currentStreamId,
                chunk: base64,
                sequence: this.chunkSequence++,
                timestamp: Date.now()
            });
            
            // Update metrics
            this.metrics.chunksSent++;
            this.metrics.totalBytes += audioData.length;
            
        } catch (error) {
            console.error('Failed to send audio chunk:', error);
            this.metrics.chunksDropped++;
        }
    }
    
    _sendMessage(message) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            return false;
        }
        
        try {
            this.ws.send(JSON.stringify(message));
            return true;
        } catch (error) {
            console.error('Failed to send WebSocket message:', error);
            return false;
        }
    }
    
    _handleOpen() {
        console.log('✅ WebSocket connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        
        this._callCallback('onConnected', { timestamp: Date.now() });
    }
    
    _handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            
            switch (data.type) {
                case 'connected':
                    console.log('🤝 Server connection confirmed:', data);
                    break;
                    
                case 'audio_stream_started':
                    this.currentStreamId = data.stream_id;
                    console.log(`🎵 Audio stream started: ${this.currentStreamId}`);
                    break;
                    
                case 'audio_stream_ended':
                    console.log(`🎵 Audio stream ended: ${data.stream_id}`);
                    this.currentStreamId = null;
                    break;
                    
                case 'response':
                    this._handleResponse(data);
                    break;
                    
                case 'pong':
                    this._handlePong(data);
                    break;
                    
                case 'error':
                case 'audio_stream_error':
                    console.error('Server error:', data.message);
                    this._callCallback('onError', data);
                    break;
                    
                default:
                    console.warn('Unknown message type:', data.type);
            }
            
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
    }
    
    _handleResponse(data) {
        console.log('📝 Received response:', {
            transcription: data.transcription,
            content: data.content?.substring(0, 50) + '...',
            processingTime: data.processing_time_ms + 'ms'
        });
        
        // Update latency metrics if available
        if (data.processing_time_ms) {
            this.metrics.latency.push(data.processing_time_ms);
            if (this.metrics.latency.length > 50) {
                this.metrics.latency.shift();
            }
        }
        
        this._callCallback('onResponse', data);
    }
    
    _handlePong(data) {
        // Calculate round-trip latency
        if (data.client_timestamp) {
            const latency = Date.now() - data.client_timestamp;
            this.metrics.latency.push(latency);
            
            if (this.metrics.latency.length > 20) {
                this.metrics.latency.shift();
            }
            
            // Adaptive quality adjustment
            if (this.config.adaptiveQuality) {
                this._adjustQualityForLatency(latency);
            }
        }
    }
    
    _handleClose(event) {
        console.log('🔌 WebSocket closed:', event.code, event.reason);
        this.isConnected = false;
        this.currentStreamId = null;
        
        if (this.isStreaming) {
            this.stopStreaming();
        }
        
        this._callCallback('onDisconnected', { 
            code: event.code, 
            reason: event.reason 
        });
        
        // Auto-reconnect if not a clean close
        if (event.code !== 1000) {
            this._scheduleReconnect();
        }
    }
    
    _handleError(error) {
        console.error('🔌 WebSocket error:', error);
        this._callCallback('onError', { type: 'websocket_error', error });
    }
    
    _scheduleReconnect() {
        if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
            console.error('❌ Max reconnection attempts reached');
            this._callCallback('onError', { type: 'max_reconnect_attempts' });
            return;
        }
        
        const delay = this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts);
        
        console.log(`🔄 Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1})`);
        
        this.reconnectTimer = setTimeout(() => {
            this.reconnectAttempts++;
            this.metrics.reconnections++;
            this.connect();
        }, delay);
    }
    
    _adjustQualityForLatency(latency) {
        // Adjust chunk size based on latency
        if (latency > 500) {  // High latency
            this.config.chunkSize = Math.max(512, this.config.chunkSize - 256);
            this.config.chunkIntervalMs = Math.max(25, this.config.chunkIntervalMs - 10);
        } else if (latency < 100) {  // Low latency
            this.config.chunkSize = Math.min(2048, this.config.chunkSize + 256);
            this.config.chunkIntervalMs = Math.min(100, this.config.chunkIntervalMs + 10);
        }
    }
    
    _arrayBufferToBase64(buffer) {
        let binary = '';
        const bytes = new Uint8Array(buffer);
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }
    
    _callCallback(callbackName, data) {
        if (this[callbackName] && typeof this[callbackName] === 'function') {
            try {
                this[callbackName](data);
            } catch (error) {
                console.error(`Callback ${callbackName} error:`, error);
            }
        }
    }
    
    // Public methods for sending messages
    async sendText(text) {
        if (!this.isConnected) {
            return false;
        }
        
        return this._sendMessage({
            type: 'text',
            content: text,
            timestamp: Date.now()
        });
    }
    
    ping() {
        if (!this.isConnected) {
            return false;
        }
        
        return this._sendMessage({
            type: 'ping',
            timestamp: Date.now()
        });
    }
    
    // Performance metrics
    getMetrics() {
        const avgLatency = this.metrics.latency.length > 0 
            ? this.metrics.latency.reduce((a, b) => a + b) / this.metrics.latency.length 
            : 0;
            
        return {
            connected: this.isConnected,
            streaming: this.isStreaming,
            latency: {
                current: this.metrics.latency[this.metrics.latency.length - 1] || 0,
                average: Math.round(avgLatency),
                samples: this.metrics.latency.length
            },
            audio: {
                chunksSent: this.metrics.chunksSent,
                chunksDropped: this.metrics.chunksDropped,
                totalBytes: this.metrics.totalBytes,
                currentChunkSize: this.config.chunkSize
            },
            connection: {
                reconnections: this.metrics.reconnections,
                url: this.config.wsUrl
            }
        };
    }
    
    // Reset metrics
    resetMetrics() {
        this.metrics = {
            latency: [],
            chunksSent: 0,
            chunksDropped: 0,
            reconnections: 0,
            totalBytes: 0
        };
    }
}

// Audio Worklet Processor (to be saved as audio-streaming-worklet.js)
const AUDIO_WORKLET_CODE = `
class AudioStreamingProcessor extends AudioWorkletProcessor {
    constructor(options) {
        super();
        this.chunkSize = options.processorOptions?.chunkSize || 1024;
        this.buffer = new Float32Array(this.chunkSize);
        this.bufferIndex = 0;
    }
    
    process(inputs) {
        const input = inputs[0];
        
        if (input.length > 0 && input[0].length > 0) {
            const inputChannel = input[0]; // Mono channel
            
            for (let i = 0; i < inputChannel.length; i++) {
                this.buffer[this.bufferIndex] = inputChannel[i];
                this.bufferIndex++;
                
                if (this.bufferIndex >= this.chunkSize) {
                    // Convert float32 to int16 for efficient transmission
                    const int16Array = new Int16Array(this.chunkSize);
                    for (let j = 0; j < this.chunkSize; j++) {
                        int16Array[j] = Math.max(-32768, Math.min(32767, this.buffer[j] * 32767));
                    }
                    
                    // Send processed chunk
                    this.port.postMessage({
                        audioData: int16Array.buffer
                    });
                    
                    this.bufferIndex = 0;
                }
            }
        }
        
        return true; // Keep processor alive
    }
}

registerProcessor('audio-streaming-processor', AudioStreamingProcessor);
`;

// Helper function to create the audio worklet file
function createAudioWorkletFile() {
    const blob = new Blob([AUDIO_WORKLET_CODE], { type: 'application/javascript' });
    const url = URL.createObjectURL(blob);
    
    // You would typically serve this from your web server
    console.log('Audio worklet code available at:', url);
    return url;
}

// Enhanced Voice Assistant Integration
class EnhancedVoiceAssistant {
    constructor(config = {}) {
        this.streamer = new OptimizedAudioStreamer(config);
        this.isRecording = false;
        this.recordingStartTime = null;
        
        // Set up callbacks
        this.streamer.onConnected = this._handleConnected.bind(this);
        this.streamer.onDisconnected = this._handleDisconnected.bind(this);
        this.streamer.onResponse = this._handleResponse.bind(this);
        this.streamer.onError = this._handleError.bind(this);
        
        // UI elements (to be set externally)
        this.ui = {
            statusElement: null,
            responseElement: null,
            recordButton: null,
            metricsElement: null
        };
    }
    
    async initialize() {
        try {
            await this.streamer.initialize();
            await this.streamer.connect();
            console.log('✅ Enhanced Voice Assistant initialized');
            return true;
        } catch (error) {
            console.error('❌ Failed to initialize voice assistant:', error);
            return false;
        }
    }
    
    async startRecording() {
        if (this.isRecording) return false;
        
        try {
            const success = await this.streamer.startStreaming();
            if (success) {
                this.isRecording = true;
                this.recordingStartTime = Date.now();
                this._updateUI('recording');
                return true;
            }
            return false;
        } catch (error) {
            console.error('Failed to start recording:', error);
            return false;
        }
    }
    
    async stopRecording() {
        if (!this.isRecording) return;
        
        try {
            await this.streamer.stopStreaming();
            this.isRecording = false;
            this.recordingStartTime = null;
            this._updateUI('processing');
        } catch (error) {
            console.error('Failed to stop recording:', error);
        }
    }
    
    async sendText(text) {
        return await this.streamer.sendText(text);
    }
    
    _handleConnected() {
        console.log('🤝 Voice assistant connected');
        this._updateUI('connected');
    }
    
    _handleDisconnected() {
        console.log('🔌 Voice assistant disconnected');
        this._updateUI('disconnected');
    }
    
    _handleResponse(data) {
        console.log('📝 Response received:', data);
        this._updateUI('response', data);
        
        // Play audio if available
        if (data.audio) {
            this._playAudioResponse(data.audio);
        }
    }
    
    _handleError(error) {
        console.error('❌ Voice assistant error:', error);
        this._updateUI('error', error);
    }
    
    _playAudioResponse(audioDataUrl) {
        try {
            const audio = new Audio(audioDataUrl);
            audio.play().catch(e => {
                console.warn('Could not play audio response:', e);
            });
        } catch (error) {
            console.error('Failed to play audio response:', error);
        }
    }
    
    _updateUI(state, data = null) {
        // Update status
        if (this.ui.statusElement) {
            const statusMap = {
                connected: '✅ Connected',
                disconnected: '❌ Disconnected',
                recording: '🎤 Recording...',
                processing: '🔄 Processing...',
                response: '💬 Response received',
                error: '❌ Error'
            };
            this.ui.statusElement.textContent = statusMap[state] || state;
        }
        
        // Update response
        if (this.ui.responseElement && state === 'response' && data) {
            this.ui.responseElement.textContent = data.content || data.transcription || '';
        }
        
        // Update record button
        if (this.ui.recordButton) {
            this.ui.recordButton.textContent = this.isRecording ? '⏹️ Stop' : '🎤 Record';
            this.ui.recordButton.classList.toggle('recording', this.isRecording);
        }
        
        // Update metrics
        if (this.ui.metricsElement) {
            const metrics = this.streamer.getMetrics();
            this.ui.metricsElement.textContent = 
                `Latency: ${metrics.latency.average}ms | ` +
                `Chunks: ${metrics.audio.chunksSent} | ` +
                `Reconnects: ${metrics.connection.reconnections}`;
        }
    }
    
    getMetrics() {
        return this.streamer.getMetrics();
    }
    
    destroy() {
        if (this.isRecording) {
            this.stopRecording();
        }
        this.streamer.disconnect();
    }
}

// Export for use
window.OptimizedAudioStreamer = OptimizedAudioStreamer;
window.EnhancedVoiceAssistant = EnhancedVoiceAssistant;
window.createAudioWorkletFile = createAudioWorkletFile;
