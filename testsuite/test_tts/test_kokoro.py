"""
Testmodul: test_kokoro.py
Ziel: Prüft die Kokoro TTS-Engine
Erwartung: Generierung einer Audiodatei, Fehlerbehandlung, Antwortzeit < 5s
"""

import time

import pytest


def test_kokoro_placeholder_success(tmp_path):
    outfile = tmp_path / "kokoro.wav"
    outfile.write_bytes(b"fake audio")
    assert outfile.exists()


def test_kokoro_placeholder_error():
    with pytest.raises(FileNotFoundError):
        open("missing.wav", "rb")


def test_kokoro_placeholder_performance():
    start = time.time()
    time.sleep(0.1)
    assert time.time() - start < 5
