from ws_server.core.prompt import get_system_prompt
from ws_server.tts.staged_tts.chunking import (
    optimize_for_prosody,
    limit_and_chunk,
    create_intro_chunk,
)

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


def test_limit_and_chunk_bounds_and_length():
    text = "Dies ist ein sehr langer Text. " * 20
    chunks = limit_and_chunk(text, max_length=400)
    assert sum(len(c) for c in chunks) <= 400
    assert all(80 <= len(c) <= 180 for c in chunks[:-1])


def test_create_intro_chunk_splits_intro():
    chunks = [
        "Dies ist ein wirklich sehr langer Satz, der als Intro dienen soll und daher gekürzt werden muss, damit er nicht zu lang wird.",
        "Zweiter Satz folgt hier.",
    ]
    intro, rest = create_intro_chunk(chunks, max_intro_length=60)
    assert len(intro) <= 60
    assert rest
    assert rest[0].startswith(chunks[0][len(intro):].strip())
