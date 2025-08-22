from ws_server.core.prompt import get_system_prompt
from ws_server.tts.staged_tts.chunking import optimize_for_prosody

def test_system_prompt_clean_and_short():
    prompt = get_system_prompt()
    assert len(prompt) <= 500
    assert "\n" not in prompt
    assert "*" not in prompt and "#" not in prompt


def test_optimize_for_prosody_strips_markdown():
    text = "- Punkt eins\n- **fett** und [link](http://example.com)"  # noqa: E501
    result = optimize_for_prosody(text)
    assert "*" not in result
    assert "[" not in result and "]" not in result
    assert "link" in result
    assert "\n" not in result
