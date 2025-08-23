from __future__ import annotations

"""Helper utilities for voice normalization."""

from typing import Optional


def canonicalize_voice(voice: Optional[str]) -> Optional[str]:
    """Return canonical voice identifier.

    Normalizes locale-style prefixes like ``de_DE-`` to ``de-`` and strips
    surrounding whitespace.  The function is intentionally minimal and can be
    extended with more rules as new voices are added.
    """
    if not voice:
        return voice
    v = voice.strip().replace("de_DE-", "de-")
    return v.lower()

__all__ = ["canonicalize_voice"]
