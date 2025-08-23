import json
import unicodedata
from ws_server.tts.text_normalize import sanitize_for_tts


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
    words = ["façade", "garçon", "Curaçao", "Soi\u0327c"]
    for w in words:
        s = sanitize_for_tts(w)
        for ch in s:
            if ch.strip():
                assert ch in model_set
