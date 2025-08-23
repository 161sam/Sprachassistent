/**
 * 🎵 Enhanced Audio Streaming Worklet Processor
 *
 * GPU-accelerated audio processing worklet with VAD support
 * Features:
 * - Real-time Voice Activity Detection (VAD)
 * - RMS and spectral analysis
 * - Adaptive noise gating
 * - Binary frame preparation
 * - Performance monitoring
 */
// TODO: clarify whether a separate AudioWorklet is still required or can be
//       merged with main streaming logic
//       (see TODO-Index.md: ❓/AudioWorklets)

class AudioStreamingProcessor extends AudioWorkletProcessor {
    constructor(options) {
        super();
        
        // Configuration from main thread
        this.chunkSize = options?.processorOptions?.chunkSize || 1024;
        this.sampleRate = options?.processorOptions?.sampleRate || 16000;
        this.channels = options?.processorOptions?.channels || 1;
        
        // VAD configuration
        this.vadEnabled = options?.processorOptions?.vadEnabled || false;
        this.vadWindowSize = options?.processorOptions?.vadWindowSize || 2048;
        this.vadThreshold = options?.processorOptions?.vadThreshold || 0.01;
        this.vadSmoothingFactor = 0.95; // For RMS smoothing
        
        // Audio buffers
        this.buffer = new Float32Array(this.chunkSize);
        this.bufferIndex = 0;
        
        // VAD processing buffers
        this.vadBuffer = new Float32Array(this.vadWindowSize);
        this.vadBufferIndex = 0;
        this.rmsHistory = new Float32Array(50); // Last 50 RMS values
        this.rmsHistoryIndex = 0;
        this.smoothedRMS = 0;
        
        // Spectral analysis for VAD
        this.fftBuffer = new Float32Array(this.vadWindowSize);
        this.hammingWindow = this.generateHammingWindow(this.vadWindowSize);
        
        // Performance monitoring
        this.processedFrames = 0;
        this.vadActivations = 0;
        this.lastMetricsUpdate = 0;
        this.totalEnergy = 0;
        this.silentFrames = 0;
        
        // Adaptive noise gate
        this.noiseFloor = 0.001;
        this.adaptiveThreshold = this.vadThreshold;
        
        console.log(`🎵 Enhanced AudioStreamingProcessor initialized: 
            Chunk: ${this.chunkSize}, Rate: ${this.sampleRate}Hz, VAD: ${this.vadEnabled}`);
    }
    
    process(inputs, outputs, parameters) {
        const input = inputs[0];
        
        // Check if we have audio input
        if (input.length > 0 && input[0].length > 0) {
            const inputChannel = input[0]; // First channel (mono)
            
            // Process each sample
            for (let i = 0; i < inputChannel.length; i++) {
                let sample = inputChannel[i];
                
                // Apply adaptive noise gate
                if (Math.abs(sample) < this.noiseFloor) {
                    sample = 0;
                    this.silentFrames++;
                } else {
                    this.silentFrames = 0;
                }
                
                // Add to main buffer
                this.buffer[this.bufferIndex] = sample;
                this.bufferIndex++;
                
                // Add to VAD buffer if enabled
                if (this.vadEnabled) {
                    this.vadBuffer[this.vadBufferIndex] = sample;
                    this.vadBufferIndex++;
                    
                    // Process VAD when buffer is full
                    if (this.vadBufferIndex >= this.vadWindowSize) {
                        this.processVAD();
                        // Overlap VAD buffer by 50% for smoother detection
                        this.copyBuffer(this.vadBuffer, this.vadWindowSize / 2, this.vadBuffer, 0, this.vadWindowSize / 2);
                        this.vadBufferIndex = this.vadWindowSize / 2;
                    }
                }
                
                // When main buffer is full, send to main thread
                if (this.bufferIndex >= this.chunkSize) {
                    this.sendAudioChunk();
                    this.bufferIndex = 0;
                }
            }
            
            this.processedFrames += inputChannel.length;
            this.totalEnergy += this.calculateArrayEnergy(inputChannel);
        }
        
        // Send periodic metrics
        const now = currentTime;
        if (now - this.lastMetricsUpdate > 0.5) { // Every 500ms
            this.sendMetrics();
            this.lastMetricsUpdate = now;
        }
        
        // Adapt noise floor based on recent activity
        if (this.silentFrames > this.sampleRate) { // 1 second of silence
            this.adaptNoiseFloor();
        }
        
        return true;
    }
    
    processVAD() {
        // Calculate RMS energy
        const rms = this.calculateRMS(this.vadBuffer);
        this.updateRMSHistory(rms);
        
        // Apply smoothing
        this.smoothedRMS = this.vadSmoothingFactor * this.smoothedRMS + (1 - this.vadSmoothingFactor) * rms;
        
        // Calculate spectral features
        const spectralFeatures = this.calculateSpectralFeatures(this.vadBuffer);
        
        // Voice activity decision
        const isVoiceActive = this.detectVoiceActivity(this.smoothedRMS, spectralFeatures);
        
        if (isVoiceActive) {
            this.vadActivations++;
        }
        
        // Send VAD info to main thread
        this.port.postMessage({
            type: 'vadInfo',
            vadInfo: {
                rms: this.smoothedRMS,
                isActive: isVoiceActive,
                spectralCentroid: spectralFeatures.centroid,
                spectralSpread: spectralFeatures.spread,
                timestamp: currentTime
            }
        });
    }
    
    calculateRMS(buffer) {
        let sumSquares = 0;
        for (let i = 0; i < buffer.length; i++) {
            sumSquares += buffer[i] * buffer[i];
        }
        return Math.sqrt(sumSquares / buffer.length);
    }
    
    updateRMSHistory(rms) {
        this.rmsHistory[this.rmsHistoryIndex] = rms;
        this.rmsHistoryIndex = (this.rmsHistoryIndex + 1) % this.rmsHistory.length;
    }
    
    calculateSpectralFeatures(buffer) {
        // Apply Hamming window
        for (let i = 0; i < buffer.length; i++) {
            this.fftBuffer[i] = buffer[i] * this.hammingWindow[i];
        }
        
        // Simple spectral analysis (without full FFT for performance)
        // Calculate spectral centroid and spread approximation
        let spectralSum = 0;
        let weightedSum = 0;
        const nyquist = this.sampleRate / 2;
        
        // Analyze frequency bins (simplified)
        const binCount = Math.min(512, buffer.length / 2);
        for (let i = 1; i < binCount; i++) {
            const frequency = (i / binCount) * nyquist;
            const magnitude = Math.abs(this.fftBuffer[i]);
            
            spectralSum += magnitude;
            weightedSum += frequency * magnitude;
        }
        
        const centroid = spectralSum > 0 ? weightedSum / spectralSum : 0;
        
        // Calculate spectral spread
        let spreadSum = 0;
        for (let i = 1; i < binCount; i++) {
            const frequency = (i / binCount) * nyquist;
            const magnitude = Math.abs(this.fftBuffer[i]);
            spreadSum += Math.pow(frequency - centroid, 2) * magnitude;
        }
        const spread = spectralSum > 0 ? Math.sqrt(spreadSum / spectralSum) : 0;
        
        return { centroid, spread };
    }
    
    detectVoiceActivity(rms, spectralFeatures) {
        // Multi-criteria VAD decision
        const energyThreshold = this.adaptiveThreshold;
        const minVoiceFreq = 85;   // Human voice starts around 85Hz
        const maxVoiceFreq = 8000; // Most speech energy below 8kHz
        
        // Energy-based detection
        const hasEnergy = rms > energyThreshold;
        
        // Spectral-based detection (check if energy is in voice range)
        const inVoiceRange = spectralFeatures.centroid > minVoiceFreq && 
                            spectralFeatures.centroid < maxVoiceFreq;
        
        // Combine criteria
        return hasEnergy && inVoiceRange;
    }
    
    adaptNoiseFloor() {
        // Calculate average RMS from history to estimate noise floor
        let avgRMS = 0;
        for (let i = 0; i < this.rmsHistory.length; i++) {
            avgRMS += this.rmsHistory[i];
        }
        avgRMS /= this.rmsHistory.length;
        
        // Update noise floor (be conservative)
        this.noiseFloor = Math.min(this.noiseFloor, avgRMS * 0.5);
        this.adaptiveThreshold = Math.max(this.vadThreshold, this.noiseFloor * 3);
    }
    
    generateHammingWindow(size) {
        const window = new Float32Array(size);
        for (let i = 0; i < size; i++) {
            window[i] = 0.54 - 0.46 * Math.cos(2 * Math.PI * i / (size - 1));
        }
        return window;
    }
    
    calculateArrayEnergy(array) {
        let energy = 0;
        for (let i = 0; i < array.length; i++) {
            energy += array[i] * array[i];
        }
        return energy;
    }
    
    copyBuffer(src, srcOffset, dest, destOffset, length) {
        for (let i = 0; i < length; i++) {
            dest[destOffset + i] = src[srcOffset + i];
        }
    }
    
    sendAudioChunk() {
        // Convert Float32 to Int16 for efficient transmission
        const int16Array = new Int16Array(this.chunkSize);
        
        for (let i = 0; i < this.chunkSize; i++) {
            // Convert float32 (-1.0 to 1.0) to int16 (-32768 to 32767)
            const sample = Math.max(-1, Math.min(1, this.buffer[i]));
            int16Array[i] = Math.round(sample * 32767);
        }
        
        // Calculate chunk-level VAD info
        const chunkRMS = this.calculateRMS(this.buffer);
        
        // Send to main thread with VAD info
        this.port.postMessage({
            type: 'audioData',
            audioData: int16Array.buffer,
            vadInfo: this.vadEnabled ? {
                rms: chunkRMS,
                timestamp: currentTime
            } : null,
            timestamp: currentTime,
            chunkSize: this.chunkSize,
            sequence: Math.floor(this.processedFrames / this.chunkSize)
        });
    }
    
    sendMetrics() {
        const avgEnergy = this.totalEnergy / Math.max(1, this.processedFrames);
        
        this.port.postMessage({
            type: 'metrics',
            data: {
                processedFrames: this.processedFrames,
                bufferUtilization: this.bufferIndex / this.chunkSize,
                vadActivations: this.vadActivations,
                avgEnergy: avgEnergy,
                noiseFloor: this.noiseFloor,
                adaptiveThreshold: this.adaptiveThreshold,
                smoothedRMS: this.smoothedRMS,
                timestamp: currentTime
            }
        });
        
        // Reset counters
        this.processedFrames = 0;
        this.vadActivations = 0;
        this.totalEnergy = 0;
    }
    
    // Handle parameter changes from main thread
    static get parameterDescriptors() {
        return [
            {
                name: 'vadThreshold',
                defaultValue: 0.01,
                minValue: 0.001,
                maxValue: 0.1
            },
            {
                name: 'noiseGate',
                defaultValue: 0.001,
                minValue: 0.0001,
                maxValue: 0.01
            }
        ];
    }
}

// Register the enhanced processor
registerProcessor('audio-streaming-processor', AudioStreamingProcessor);
