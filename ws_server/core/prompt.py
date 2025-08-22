"""LLM system prompt helpers."""

from ws_server.tts.staged_tts import _limit_and_chunk
from ws_server.core.config import config


def get_system_prompt(max_length: int = 500) -> str:
    """Return the system prompt limited to ``max_length`` characters."""

    prompt = " ".join(config.llm_system_prompt.split())
    return _limit_and_chunk(prompt, max_length)[0]


__all__ = ["get_system_prompt"]

