from ws_server.tts.engines.zonos import normalize_lang


def test_normalize_lang_german_variants():
    assert normalize_lang("de-de") == "de"
    assert normalize_lang("DE_de") == "de"
    assert normalize_lang(None) == "de"

