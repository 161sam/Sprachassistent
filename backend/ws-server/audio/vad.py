#!/usr/bin/env python3
"""
Simple Voice Activity Detection (VAD) implementation
for automatic speech end detection in the voice assistant.
"""

import numpy as np
import logging
from typing import Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class VADConfig:
    """Configuration for Voice Activity Detection"""
    sample_rate: int = 16000
    frame_duration_ms: int = 30  # 30ms frames
    energy_threshold: float = 0.01  # RMS energy threshold
    freq_threshold: tuple = (80, 4000)  # Voice frequency range in Hz
    silence_duration_ms: int = 1500  # 1.5s of silence to trigger stop
    min_speech_duration_ms: int = 500  # Minimum 0.5s of speech before VAD can trigger
    energy_history_size: int = 10  # Number of frames to average for adaptive threshold

class VoiceActivityDetector:
    """
    Simple VAD implementation using energy and frequency analysis.
    
    Features:
    - RMS energy-based voice detection
    - Frequency band filtering for human voice
    - Adaptive thresholding based on background noise
    - Configurable silence duration for auto-stop
    """
    
    def __init__(self, config: VADConfig = None):
        self.config = config or VADConfig()
        self.frame_size = int(self.config.sample_rate * self.config.frame_duration_ms / 1000)
        self.silence_frames_threshold = int(self.config.silence_duration_ms / self.config.frame_duration_ms)
        self.min_speech_frames = int(self.config.min_speech_duration_ms / self.config.frame_duration_ms)
        
        # State tracking
        self.energy_history: List[float] = []
        self.speech_frames = 0
        self.silence_frames = 0
        self.adaptive_threshold = self.config.energy_threshold
        self.is_speech_started = False
        
        logger.info(f"VAD initialized: frame_size={self.frame_size}, silence_threshold={self.silence_frames_threshold}")
    
    def reset(self):
        """Reset VAD state for new recording session"""
        self.energy_history.clear()
        self.speech_frames = 0
        self.silence_frames = 0
        self.is_speech_started = False
        self.adaptive_threshold = self.config.energy_threshold
        
    def process_frame(self, audio_data: np.ndarray) -> bool:
        """
        Process audio frame and return True if speech should continue.
        
        Args:
            audio_data: Audio frame as numpy array (float32, normalized)
            
        Returns:
            True if recording should continue, False if auto-stop should trigger
        """
        try:
            # Calculate RMS energy
            energy = np.sqrt(np.mean(audio_data ** 2))
            
            # Update energy history for adaptive thresholding
            self.energy_history.append(energy)
            if len(self.energy_history) > self.config.energy_history_size:
                self.energy_history.pop(0)
            
            # Update adaptive threshold (use median of recent energy levels)
            if len(self.energy_history) >= 3:
                self.adaptive_threshold = max(
                    np.median(self.energy_history) * 1.5,
                    self.config.energy_threshold
                )
            
            # Simple frequency analysis (optional enhancement)
            is_voice_frequency = self._check_voice_frequency(audio_data)
            
            # Voice activity detection
            is_speech = energy > self.adaptive_threshold and is_voice_frequency
            
            if is_speech:
                self.speech_frames += 1
                self.silence_frames = 0
                
                # Mark speech as started after minimum duration
                if self.speech_frames >= self.min_speech_frames:
                    self.is_speech_started = True
                    
            else:
                self.silence_frames += 1
                
            # Auto-stop logic: trigger only after speech has started and silence threshold reached
            should_stop = (
                self.is_speech_started and 
                self.silence_frames >= self.silence_frames_threshold
            )
            
            logger.debug(f"VAD: energy={energy:.4f}, threshold={self.adaptive_threshold:.4f}, "
                        f"speech_frames={self.speech_frames}, silence_frames={self.silence_frames}, "
                        f"should_stop={should_stop}")
            
            return not should_stop
            
        except Exception as e:
            logger.error(f"VAD processing error: {e}")
            return True  # Continue on error
    
    def _check_voice_frequency(self, audio_data: np.ndarray) -> bool:
        """
        Simple frequency analysis to check if audio contains voice frequencies.
        
        This is a basic implementation - could be enhanced with proper FFT analysis.
        """
        try:
            # For now, just check if audio has reasonable variation (not just noise)
            variation = np.std(audio_data)
            return variation > 0.001  # Basic noise gate
            
        except Exception:
            return True  # Assume voice-like on error
    
    def get_stats(self) -> dict:
        """Get current VAD statistics"""
        return {
            'speech_frames': self.speech_frames,
            'silence_frames': self.silence_frames,
            'adaptive_threshold': self.adaptive_threshold,
            'is_speech_started': self.is_speech_started,
            'energy_history_length': len(self.energy_history)
        }

def create_vad_processor(sample_rate: int = 16000, 
                        silence_duration_ms: int = 1500,
                        energy_threshold: float = 0.01) -> VoiceActivityDetector:
    """
    Factory function to create a VAD processor with custom settings.
    
    Args:
        sample_rate: Audio sample rate in Hz
        silence_duration_ms: Silence duration to trigger auto-stop
        energy_threshold: Base energy threshold for voice detection
        
    Returns:
        Configured VoiceActivityDetector instance
    """
    config = VADConfig(
        sample_rate=sample_rate,
        silence_duration_ms=silence_duration_ms,
        energy_threshold=energy_threshold
    )
    return VoiceActivityDetector(config)

# Example usage and testing
if __name__ == "__main__":
    # Simple test with synthetic audio
    vad = create_vad_processor()
    
    # Simulate audio frames
    sample_rate = 16000
    frame_duration = 0.03  # 30ms
    frame_size = int(sample_rate * frame_duration)
    
    # Test with silence
    silence = np.zeros(frame_size, dtype=np.float32)
    print("Testing with silence...")
    for i in range(10):
        should_continue = vad.process_frame(silence)
        print(f"Frame {i}: continue={should_continue}")
    
    # Test with speech-like signal
    print("\nTesting with speech-like signal...")
    vad.reset()
    for i in range(100):
        # Simulate speech with some noise
        if i < 80:  # Speech
            speech = np.random.normal(0, 0.1, frame_size).astype(np.float32)
        else:  # Silence
            speech = np.random.normal(0, 0.001, frame_size).astype(np.float32)
            
        should_continue = vad.process_frame(speech)
        if not should_continue:
            print(f"VAD triggered auto-stop at frame {i}")
            break
    
    print(f"Final stats: {vad.get_stats()}")
