import json
import unicodedata
from ws_server.tts.text_normalize import sanitize_for_tts
from tools.tts.phoneme_audit import PROBLEM_TEXTS, load_map, audit_texts
import pytest


def _has_mn(text: str) -> bool:
    return any(unicodedata.category(ch) == 'Mn' for ch in text)


def test_orphan_combining_removed():
    raw = "gar\u0327çon"
    s = sanitize_for_tts(raw)
    assert not _has_mn(s)


def test_nbsp_zero_width_removed():
    raw = "fa\u00A0cade\u200B"
    s = sanitize_for_tts(raw)
    assert "\u00A0" not in s and "\u200B" not in s


def test_phoneme_coverage_subset():
    with open('tests/fixtures/de_DE-thorsten-low.onnx.json', encoding='utf-8') as f:
        model_set = set(json.load(f)['phoneme_id_map'].keys())
    words = ["façade", "garçon", "c\u0327edilla", "übermäßig", "naïve"]
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
