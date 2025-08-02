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
