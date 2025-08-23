import json
import unicodedata
import logging
import pytest
from ws_server.tts.text_normalize import sanitize_for_tts
from ws_server.tts.text_sanitizer import sanitize_for_tts_strict
from tools.tts.phoneme_audit import PROBLEM_TEXTS, load_map, audit_texts


def _has_mn(text: str) -> bool:
    return any(unicodedata.category(ch) == 'Mn' for ch in text)


def test_orphan_combining_removed():
    raw = "gaŗçon"
    s = sanitize_for_tts(raw)
    assert not _has_mn(s)


def test_nbsp_zero_width_removed():
    raw = "fa cade​"
    s = sanitize_for_tts(raw)
    assert " " not in s and "​" not in s


def test_phoneme_coverage_subset():
    with open('tests/fixtures/de_DE-thorsten-low.onnx.json', encoding='utf-8') as f:
        model_set = set(json.load(f)['phoneme_id_map'].keys())
    words = ["façade", "garçon", "çedilla", "übermäßig", "naïve"]
    for w in words:
        s = sanitize_for_tts(w)
        for ch in s:
            if ch.strip():
                assert ch in model_set


def test_non_latin_removed():
    raw = "東京"
    assert sanitize_for_tts(raw) == ""


def test_phoneme_audit_problem_cases():
    pytest.importorskip('phonemizer.backend')
    model_set = load_map('tests/fixtures/de_DE-thorsten-low.onnx.json')
    sanitized = [sanitize_for_tts(t) for t in PROBLEM_TEXTS]
    unknown = audit_texts(sanitized, model_set, lang='de')
    assert unknown == set()


def test_strict_sanitizer_warns_and_cleans(caplog):
    caplog.set_level(logging.WARNING)
    cleaned = sanitize_for_tts_strict("çedilla ☃")
    assert cleaned == "cedilla"
    assert "unbekanntes Zeichen" in caplog.text
