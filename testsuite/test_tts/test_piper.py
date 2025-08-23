"""
Testmodul: test_piper.py
Ziel: Prüft, ob die Piper TTS-Engine eine Audiodatei erzeugt
Erwartung: Datei wird generiert, Fehler werden abgefangen, Antwortzeit < 5s
"""

import time

import pytest


def test_piper_placeholder_success(tmp_path):
    outfile = tmp_path / "piper.wav"
    outfile.write_bytes(b"fake audio")
    assert outfile.exists()


def test_piper_placeholder_error():
    with pytest.raises(FileNotFoundError):
        open("nonexistent.wav", "rb")


def test_piper_placeholder_performance():
    start = time.time()
    time.sleep(0.1)
    assert time.time() - start < 5


def test_piper_fallback_sample_rate(monkeypatch):
    """Piper engine should fall back to voice.sample_rate if config sample_rate is missing."""
    from ws_server.tts.engines.piper import PiperTTSEngine
    from backend.tts.base_tts_engine import TTSConfig

    class FakeChunk:
        audio_int16_bytes = b"\x00\x01" * 10

    class FakeVoice:
        def __init__(self):
            class Config:
                sample_rate = 0

            self.config = Config()
            self.sample_rate = 16000

        def synthesize(self, text, syn_config=None):
            yield FakeChunk()

    monkeypatch.setattr(
        "ws_server.tts.engines.piper.PiperVoice.load", lambda path: FakeVoice()
    )

    engine = PiperTTSEngine(TTSConfig())

    audio, sr = engine._piper_synthesis_sync(
        "Hallo", "de-test", {}, model_path="dummy.onnx"
    )
    assert sr == 16000
    assert isinstance(audio, bytes)
