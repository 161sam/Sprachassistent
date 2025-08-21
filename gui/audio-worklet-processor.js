/**
 * 🎵 Audio Worklet Processor for Voice Assistant GUI
 * 
 * Simple audio worklet processor that bridges to the main AudioStreamer
 * This is a lightweight version for the GUI compatibility
 */

class VoiceAssistantAudioProcessor extends AudioWorkletProcessor {
    constructor(options) {
        super();
        
        this.chunkSize = options?.processorOptions?.chunkSize || 1024;
        this.buffer = new Float32Array(this.chunkSize);
        this.bufferIndex = 0;
        
        console.log('🎵 VoiceAssistantAudioProcessor loaded');
    }
    
    process(inputs, outputs, parameters) {
        const input = inputs[0];
        
        if (input.length > 0 && input[0].length > 0) {
            const inputChannel = input[0];
            
            for (let i = 0; i < inputChannel.length; i++) {
                this.buffer[this.bufferIndex] = inputChannel[i];
                this.bufferIndex++;
                
                if (this.bufferIndex >= this.chunkSize) {
                    // Convert to Int16Array for transmission
                    const int16Array = new Int16Array(this.chunkSize);
                    for (let j = 0; j < this.chunkSize; j++) {
                        int16Array[j] = Math.max(-32768, Math.min(32767, this.buffer[j] * 32767));
                    }
                    
                    this.port.postMessage({
                        audioData: int16Array.buffer
                    });
                    
                    this.bufferIndex = 0;
                }
            }
        }
        
        return true;
    }
}

registerProcessor('voice-assistant-audio-processor', VoiceAssistantAudioProcessor);
