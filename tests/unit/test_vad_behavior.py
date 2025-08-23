import numpy as np
from ws_server.audio.vad import VADConfig, VoiceActivityDetector, create_vad_processor


def _create_speech_frame(vad: VoiceActivityDetector) -> np.ndarray:
    return np.random.normal(0, 0.1, vad.frame_size).astype(np.float32)


def _create_silence_frame(vad: VoiceActivityDetector) -> np.ndarray:
    return np.zeros(vad.frame_size, dtype=np.float32)


def test_vad_triggers_after_silence():
    cfg = VADConfig(silence_duration_ms=60, min_speech_duration_ms=30)
    vad = VoiceActivityDetector(cfg)
    speech = _create_speech_frame(vad)
    for _ in range(vad.min_speech_frames):
        assert vad.process_frame(speech)
    silence = _create_silence_frame(vad)
    keep = True
    for _ in range(vad.silence_frames_threshold):
        keep = vad.process_frame(silence)
    assert keep is False
    stats = vad.get_stats()
    assert stats["is_speech_started"] is True
    assert stats["silence_frames"] >= vad.silence_frames_threshold


def test_vad_process_error_returns_true():
    vad = create_vad_processor()
    assert vad.process_frame(None) is True
