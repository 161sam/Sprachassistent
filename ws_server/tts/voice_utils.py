from __future__ import annotations

"""Helper utilities for voice normalization."""

from typing import Optional


def canonicalize_voice(voice: Optional[str]) -> str:
    """Return canonical voice identifier.

    Normalizes locale prefixes like ``de_DE-`` to ``de-`` and strips
    surrounding whitespace.  The function is intentionally minimal and can be
    extended with more rules as new voices are added.
    """
    if not voice:
        return ""
    v = voice.strip().lower()
    if v.startswith("de_de-"):
        v = "de-" + v[len("de_de-") :]
    return v

__all__ = ["canonicalize_voice"]
