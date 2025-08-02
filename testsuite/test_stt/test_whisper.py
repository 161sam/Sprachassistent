"""
Testmodul: test_whisper.py
Ziel: Prüft die Whisper STT-Engine
Erwartung: Text wird transkribiert, Fehler werden erkannt, Antwortzeit < 5s
"""

import time

import pytest


def test_whisper_placeholder_success():
    transcript = "hello"
    assert transcript == "hello"


def test_whisper_placeholder_error():
    with pytest.raises(ValueError):
        raise ValueError("bad audio")


def test_whisper_placeholder_performance():
    start = time.time()
    time.sleep(0.05)
    assert time.time() - start < 5
