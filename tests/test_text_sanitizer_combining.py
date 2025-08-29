import unicodedata

from ws_server.tts.text_sanitizer import sanitize_for_tts_strict, pre_clean_for_piper


def test_combining_cedilla_removed_strict():
    # build a string with combining cedilla (U+0327)
    s = "Fran\u00E7ois c\u0327a va?"  # 'François ça va?'
    # ensure combining char is present in source
    assert "\u0327" in s or any(unicodedata.category(ch) == "Mn" for ch in s)
    out = sanitize_for_tts_strict(s)
    # No combining marks remain
    assert all(unicodedata.category(ch) != "Mn" for ch in out)
    # Base letters preserved roughly
    assert "Francois" in unicodedata.normalize("NFKD", out)


def test_pre_clean_for_piper_no_combining():
    s = "c\u0327"  # c + combining cedilla
    out = pre_clean_for_piper(s)
    assert out == "c"
    assert all(unicodedata.category(ch) != "Mn" for ch in out)

