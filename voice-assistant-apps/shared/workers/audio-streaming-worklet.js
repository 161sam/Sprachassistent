/**
 * 🎵 Audio Streaming Worklet Processor
 * 
 * GPU-accelerated audio processing worklet for real-time streaming
 * Runs on dedicated audio thread for minimal latency
 */

class AudioStreamingProcessor extends AudioWorkletProcessor {
    constructor(options) {
        super();
        
        // Configuration from main thread
        this.chunkSize = options?.processorOptions?.chunkSize || 1024;
        this.sampleRate = options?.processorOptions?.sampleRate || 16000;
        this.channels = options?.processorOptions?.channels || 1;
        
        // Audio buffer for chunking
        this.buffer = new Float32Array(this.chunkSize);
        this.bufferIndex = 0;
        
        // Performance monitoring
        this.processedFrames = 0;
        this.lastMetricsUpdate = 0;
        
        console.log(`🎵 AudioStreamingProcessor initialized: ${this.chunkSize} chunk, ${this.sampleRate}Hz`);
    }
    
    process(inputs, outputs, parameters) {
        const input = inputs[0];
        
        // Check if we have audio input
        if (input.length > 0 && input[0].length > 0) {
            const inputChannel = input[0]; // First channel (mono)
            
            // Process each sample
            for (let i = 0; i < inputChannel.length; i++) {
                // Apply basic audio processing
                let sample = inputChannel[i];
                
                // Simple noise gate (remove very quiet signals)
                if (Math.abs(sample) < 0.001) {
                    sample = 0;
                }
                
                // Add to buffer
                this.buffer[this.bufferIndex] = sample;
                this.bufferIndex++;
                
                // When buffer is full, send to main thread
                if (this.bufferIndex >= this.chunkSize) {
                    this.sendAudioChunk();
                    this.bufferIndex = 0;
                }
            }
            
            this.processedFrames += inputChannel.length;
        }
        
        // Send periodic metrics (every 1 second)
        const now = currentTime;
        if (now - this.lastMetricsUpdate > 1.0) {
            this.sendMetrics();
            this.lastMetricsUpdate = now;
        }
        
        // Keep processor alive
        return true;
    }
    
    sendAudioChunk() {
        // Convert Float32 to Int16 for efficient transmission
        const int16Array = new Int16Array(this.chunkSize);
        
        for (let i = 0; i < this.chunkSize; i++) {
            // Convert float32 (-1.0 to 1.0) to int16 (-32768 to 32767)
            const sample = Math.max(-1, Math.min(1, this.buffer[i]));
            int16Array[i] = Math.round(sample * 32767);
        }
        
        // Send to main thread
        this.port.postMessage({
            type: 'audioData',
            audioData: int16Array.buffer,
            timestamp: currentTime,
            chunkSize: this.chunkSize
        });
    }
    
    sendMetrics() {
        this.port.postMessage({
            type: 'metrics',
            data: {
                processedFrames: this.processedFrames,
                bufferUtilization: this.bufferIndex / this.chunkSize,
                timestamp: currentTime
            }
        });
        
        // Reset frame counter
        this.processedFrames = 0;
    }
    
    // Handle messages from main thread
    static get parameterDescriptors() {
        return [];
    }
}

// Register the processor
registerProcessor('audio-streaming-processor', AudioStreamingProcessor);
