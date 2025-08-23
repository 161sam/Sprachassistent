#!/usr/bin/env python3
"""Utility functions for strict text sanitization in the TTS pipeline."""

import os
import re
import unicodedata
import logging
from typing import Dict

logger = logging.getLogger(__name__)

_TYPOMAP = {
    "\u2013": "-", "\u2014": "-", "\u2212": "-",
    "\u2018": "'", "\u2019": "'",
    "\u201C": '"', "\u201D": '"', "\u201E": '"',
    "\u2026": "...",
    "\u00A0": " ",
}
_COMBINING_RE = re.compile(r"[̀-ͯ]")
_ALLOWED = set("abcdefghijklmnopqrstuvwxyzäöüßABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜß0123456789 .,!?;:-'\"()")


def sanitize_for_tts_strict(text: str) -> str:
    """Normalize text and remove all combining marks (Mn).

    Steps: NFKC -> NFD -> drop Mn -> typographic replacements ->
    whitespace compression.
    """
    if not text:
        return text
    t = unicodedata.normalize("NFKC", text)
    t = unicodedata.normalize("NFD", t)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    t = t.translate(str.maketrans(_TYPOMAP))
    cleaned: list[str] = []
    for ch in t:
        if ord(ch) > 127 and ch not in _ALLOWED:
            logger.warning("Entferne unbekanntes Zeichen %r (U+%04X)", ch, ord(ch))
            continue
        cleaned.append(ch)
    t = "".join(cleaned)
    t = re.sub(r"\s+", " ", t).strip()
    return unicodedata.normalize("NFC", t)


def pre_clean_for_piper(text: str) -> str:
    """Final guard before Piper synthesis.

    Ensures no combining marks remain (U+0300–U+036F) and applies
    Piper specific replacements such as removing the combining cedilla.
    """
    if not text:
        return text
    original = text
    t = sanitize_for_tts_strict(text)
    t = t.replace("\u0327", "")  # combining cedilla
    t = _COMBINING_RE.sub("", t)
    if t != original:
        removed = len(original) - len(t)
        logger.warning("pre_clean_for_piper entfernte %d Zeichen", removed)
    return t


def analyze_problematic_chars(text: str) -> Dict[str, any]:
    """Return a summary of non-ASCII or combining characters."""
    if not text:
        return {}
    unknown = [ch for ch in text if (ord(ch) > 127 and ch not in "äöüÄÖÜß") or unicodedata.category(ch) == "Mn"]
    return {"unique": sorted(set(unknown)), "count": len(unknown)}


# Backwards compatible alias used across the codebase

def sanitize_for_tts(text: str, engine: str = "piper") -> str:  # pragma: no cover - thin wrapper
    """Alias for legacy imports; always uses the strict sanitizer."""
    return sanitize_for_tts_strict(text)

