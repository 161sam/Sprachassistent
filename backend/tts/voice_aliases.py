"""Voice alias mapping for TTS engines."""
from __future__ import annotations

# TODO: merge with ws_server/tts/voice_aliases.py to avoid configuration drift
#       (see TODO-Index.md: Config/Voice aliases)
from typing import Dict

VOICE_ALIASES: Dict[str, str] = {
    "de-thorsten-low": "de_DE-thorsten-low",
    "de_DE-thorsten-low": "de_DE-thorsten-low",
}


def resolve_voice_alias(voice: str) -> str:
    """Return canonical voice name for given alias."""
    return VOICE_ALIASES.get(voice, voice)
