"""LLM system prompt helpers."""

import os

from ws_server.tts.staged_tts import limit_and_chunk

# Default prompt can be overridden via environment for localisation
DEFAULT_PROMPT = (
    "You are a friendly voice assistant. Reply in short, natural sentences that "
    "sound like speech. Avoid lists or Markdown formatting. If something is "
    "unclear, ask a brief follow-up question."
)


def get_system_prompt(max_length: int = 500) -> str:
    """Return the system prompt limited to ``max_length`` characters."""

    prompt = os.getenv("LLM_SYSTEM_PROMPT", DEFAULT_PROMPT)
    prompt = " ".join(prompt.split())
    return limit_and_chunk(prompt, max_length)[0]


__all__ = ["get_system_prompt"]

