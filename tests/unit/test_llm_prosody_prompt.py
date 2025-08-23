import sys
import types
import pytest

from ws_server.core.prompt import get_system_prompt
from ws_server.tts.staged_tts.chunking import (
    optimize_for_prosody,
    _limit_and_chunk,
    create_intro_chunk,
)


def _get_voice_server():
    """Return a minimal ``VoiceServer`` implementation for tests.

    The real server pulls in many heavy optional dependencies.  This lightweight
    version only implements the pieces needed for exercising ``_ask_llm`` and
    related logic.
    """

    class VoiceServer:
        llm_enabled = True
        llm_model = "test"
        llm_temperature = 0.7
        llm_max_tokens = 256
        llm_max_turns = 5

        def __init__(self):
            self.chat_histories: dict[str, list[dict[str, str]]] = {}

        def _hist(self, cid: str) -> list[dict[str, str]]:
            return self.chat_histories.setdefault(cid, [])

        def _hist_trim(self, cid: str) -> None:
            hist = self.chat_histories[cid]
            while len(hist) > self.llm_max_turns:
                hist.pop(1)

        async def _ask_llm(self, client_id: str, user_text: str) -> str | None:
            if not (self.llm_enabled and self.llm_model and getattr(self, 'llm', None)):
                return None

            msgs = self._hist(client_id)
            if not msgs or msgs[0].get("role") != "system":
                msgs.insert(0, {"role": "system", "content": get_system_prompt()})
            msgs.append({"role": "user", "content": user_text})
            self._hist_trim(client_id)

            try:
                resp = await self.llm.chat(
                    model=self.llm_model,
                    messages=msgs,
                    temperature=self.llm_temperature,
                    max_tokens=self.llm_max_tokens,
                )
                choice = (resp.get("choices") or [{}])[0]
                content = (choice.get("message") or {}).get("content") or ""
                if content.strip():
                    capped = " ".join(_limit_and_chunk(content))
                    msgs.append({"role": "assistant", "content": capped})
                    self._hist_trim(client_id)
                    return capped
            except Exception:
                pass
            return None

    return VoiceServer


def test_system_prompt_clean_and_short():
    prompt = get_system_prompt()
    assert len(prompt) <= 500
    assert "\n" not in prompt
    assert "*" not in prompt and "#" not in prompt
    assert "short" in prompt.lower()
    assert "500" in prompt


def test_optimize_for_prosody_strips_markdown():
    text = "- Punkt eins\n- **fett** und [link](http://example.com)"  # noqa: E501
    result = optimize_for_prosody(text)
    assert "*" not in result
    assert "[" not in result and "]" not in result
    assert "link" in result
    assert "\n" not in result


def test_limit_and_chunk_bounds_and_length():
    text = "Dies ist ein sehr langer Text. " * 20
    chunks = _limit_and_chunk(text, max_length=400)
    assert sum(len(c) for c in chunks) <= 400
    assert all(80 <= len(c) <= 180 for c in chunks[:-1])


def test_limit_and_chunk_respects_500_char_limit():
    text = "Dies ist ein sehr langer Text. " * 40
    chunks = _limit_and_chunk(text)
    assert sum(len(c) for c in chunks) <= 500
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


@pytest.mark.asyncio
async def test_ask_llm_caps_long_response():
    VoiceServer = _get_voice_server()
    server = VoiceServer.__new__(VoiceServer)
    server.llm_enabled = True
    server.llm_model = "test"
    server.llm_temperature = 0.7
    server.llm_max_tokens = 256
    server.llm_max_turns = 5

    class DummyLLM:
        async def chat(self, *args, **kwargs):
            return {"choices": [{"message": {"content": "Wort " * 200}}]}

    server.llm = DummyLLM()
    server.chat_histories = {}
    server._hist = lambda cid: server.chat_histories.setdefault(cid, [])
    server._hist_trim = lambda cid: None

    result = await server._ask_llm("c1", "hi")
    assert result and len(result) <= 500

