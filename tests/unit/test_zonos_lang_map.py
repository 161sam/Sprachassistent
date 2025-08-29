import pytest

from ws_server.tts.engines import zonos as z


@pytest.mark.parametrize("inp,exp", [
    ("de-de", "de"), ("DE", "de"), ("german", "de"), ("deu", "de"),
    ("en-us", "en"), ("EN", "en"), ("english", "en"), ("eng", "en"),
])
def test_normalize_lang(inp, exp):
    assert z._normalize_lang(inp) == exp


def test_validate_lang_rejects_absurd():
    with pytest.raises(ValueError) as ei:
        z._validate_lang("xx-unknown")
    assert "Unsupported language" in str(ei.value)
