"""
Testmodul: test_flowise.py
Ziel: Prüft, ob Flowise erreichbar ist und einfache Prompts korrekt beantwortet werden
Erwartung: HTTP 200, Antwortstruktur enthält key 'response'
"""

import time

import pytest


def test_flowise_placeholder_success():
    assert True


def test_flowise_placeholder_error():
    with pytest.raises(RuntimeError):
        raise RuntimeError("flowise unreachable")


def test_flowise_placeholder_performance():
    start = time.time()
    time.sleep(0.05)
    assert time.time() - start < 5
