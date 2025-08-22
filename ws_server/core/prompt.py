"""LLM system prompt helpers."""

from ws_server.tts.staged_tts import limit_and_chunk

LLM_SYSTEM_PROMPT = (
    "You are a friendly voice assistant. Reply in short, natural sentences that "
    "sound like speech. Avoid lists or Markdown formatting. If something is "
    "unclear, ask a brief follow-up question."
)
# TODO: load default prompt from configuration to allow easy localization

def get_system_prompt(max_length: int = 500) -> str:
    """Return the system prompt limited to ``max_length`` characters."""
    prompt = " ".join(LLM_SYSTEM_PROMPT.split())
    return limit_and_chunk(prompt, max_length)[0]
