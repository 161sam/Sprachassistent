import unicodedata
from ws_server.tts.text_sanitizer import pre_clean_for_piper


def has_mn(text: str) -> bool:
    return any(unicodedata.category(ch) == 'Mn' for ch in text)


def test_pre_clean_various_cases():
    cases = [
        ('fa\u0327cade', 'facade'),
        ('gar\u00E7on', 'garcon'),
        ('fa\u00A0cade', 'fa cade'),
        ('voilà … — – “ ” ‘ ’', 'voila ... - - " " \' \''),
    ]
    for raw, expected in cases:
        cleaned = pre_clean_for_piper(raw)
        assert cleaned == expected
        assert not has_mn(cleaned)
        # idempotent
        assert pre_clean_for_piper(cleaned) == cleaned
