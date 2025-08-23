#!/usr/bin/env python3
"""Utility functions for strict text sanitization in the TTS pipeline."""
# ``text_normalize.basic_sanitize`` for a unified pipeline
# TODO: consolidate with text_normalize to avoid duplicate sanitization
#       (see TODO-Index.md: WS-Server / Protokolle)

import re
import unicodedata
import logging
from typing import Dict

from .text_normalize import basic_sanitize as _basic_sanitize

logger = logging.getLogger(__name__)

_TYPOMAP = {
    "\u2013": "-", "\u2014": "-", "\u2212": "-",
    "\u2018": "'", "\u2019": "'",
    "\u201C": '"', "\u201D": '"', "\u201E": '"',
    "\u2026": "...",
    "\u00A0": " ",
}
_FALLBACK_MAP = {
    "ł": "l", "Ł": "L",
    "đ": "d", "Đ": "D",
    "ø": "o", "Ø": "O",
    "ð": "d", "Ð": "D",
}
_FALLBACK_TRANSLATION = str.maketrans(_FALLBACK_MAP)
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
    t = t.translate(_FALLBACK_TRANSLATION)
    cleaned: list[str] = []
    for ch in t:
        if ch not in _ALLOWED:
            if not ch.isspace():
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
    t = unicodedata.normalize("NFC", t)
    if t != original:
        removed = len(original) - len(t)
        logger.warning("pre_clean_for_piper entfernte %d Zeichen", removed)
    return t


def pre_sanitize_text(text: str, mode: str | None = None) -> str:
    """Run basic + strict sanitizers and log removed characters."""
    if not text:
        return text
    analysis = analyze_problematic_chars(text)
    cleaned = pre_clean_for_piper(_basic_sanitize(text, mode=mode))
    if analysis.get("count"):
        logger.warning(
            "pre_sanitize_text entfernte %d Zeichen: %s",
            analysis["count"], " ".join(analysis["unique"]),
        )
    return cleaned

def analyze_problematic_chars(text: str) -> Dict[str, any]:
    """Return a summary of characters outside the allowed set."""
    if not text:
        return {}
    unknown = [
        ch
        for ch in text
        if ch not in _ALLOWED and unicodedata.category(ch)[0] != "C"
    ]
    return {"unique": sorted(set(unknown)), "count": len(unknown)}


# Backwards compatible alias used across the codebase

def sanitize_for_tts(text: str, engine: str = "piper") -> str:  # pragma: no cover - thin wrapper
    """Alias for legacy imports; always uses the strict sanitizer."""
    return sanitize_for_tts_strict(text)

