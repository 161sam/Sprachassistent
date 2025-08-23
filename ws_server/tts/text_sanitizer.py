#!/usr/bin/env python3
"""
Erweiterte Text-Bereinigung für TTS-Engines.
Entfernt u.a. kombinierende Cedilla (U+0327) und normalisiert Typographie.
"""

import re
import unicodedata
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class TTSTextSanitizer:
    def __init__(self):
        # Schnelle, sichere Ersetzungen (ASCII-kompatibel)
        self.piper_replacements = {
            # Buchstaben mit Diakritika
            'ç': 'c', 'ñ': 'n', 'ø': 'o', 'æ': 'ae', 'œ': 'oe',
            'ß': 'ss',
            # Gedankenstriche, NBSP, Ellipse
            '\u2013': '-', '\u2014': '-', '\u2212': '-',
            '\u00A0': ' ', '\u2026': '...',
            # Typographische Anführungszeichen → ASCII
            '\u2018': "'", '\u2019': "'",
            '\u201C': '"', '\u201D': '"',
        }
        # Vollständig entfernen
        self.remove_chars = {'\u200B','\u200C','\u200D','\uFEFF','\u00AD'}
        # Cleanup-Regeln
        self.cleanup_patterns = [
            (r'\s+', ' '),
            (r'\.{4,}', '...'),
            (r'-{2,}', '-'),
            (r'[_]{2,}', '_'),
            (r'\n\s*\n', '\n'),
        ]

    def sanitize_for_piper(self, text: str) -> str:
        if not text:
            return text
        orig = text
        try:
            # 1) Kompatibilitäts-Normalisierung
            text = unicodedata.normalize('NFKC', text)
            # 2) Zero-Width/Soft-Hyphen etc. entfernen
            for ch in self.remove_chars:
                text = text.replace(ch, '')
            # 3) Schnelle Ersetzungen
            for old, new in self.piper_replacements.items():
                text = text.replace(old, new)
            # 4) Kombinierende Zeichen (Mn) weg – entfernt U+0327 auch ohne Basis
            text = ''.join(
                c for c in unicodedata.normalize('NFD', text)
                if unicodedata.category(c) != 'Mn'
            )
            # 5) Cleanups
            for pat, rep in self.cleanup_patterns:
                text = re.sub(pat, rep, text)
            text = text.strip()
            if text != orig:
                logger.debug("Sanitized (piper): %r -> %r", orig, text)
            return text
        except Exception as e:
            logger.error("sanitize_for_piper failed: %s", e)
            return re.sub(r'[^\x00-\x7F]+', ' ', orig).strip()

    def sanitize_for_zonos(self, text: str) -> str:
        if not text:
            return text
        try:
            text = unicodedata.normalize('NFKC', text)
            for ch in self.remove_chars:
                text = text.replace(ch, '')
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        except Exception as e:
            logger.error("sanitize_for_zonos failed: %s", e)
            return text

    def analyze_problematic_chars(self, text: str) -> Dict:
        if not text:
            return {}
        unknown = []
        for ch in text:
            if (ord(ch) > 127 and ch not in 'äöüÄÖÜß') or (unicodedata.category(ch) == 'Mn'):
                unknown.append(ch)
        return {'unique': sorted(set(unknown)), 'count': len(unknown)}

# Modulweite Helfer
text_sanitizer = TTSTextSanitizer()

def sanitize_for_tts(text: str, engine: str = 'piper') -> str:
    eng = (engine or 'piper').lower()
    if eng == 'zonos':
        return text_sanitizer.sanitize_for_zonos(text)
    return text_sanitizer.sanitize_for_piper(text)

if __name__ == '__main__':
    samples = [
        "Hallo! Dies ist ein Test mit \u0327 Sonderzeichen.",
        "Café, naïve, résumé, façade",
        "Das kostet 19,99€ — sehr günstig!",
        "Größer ≥ kleiner… interessant.",
        '"Anführungszeichen" und \'Apostrophe\'',
        "Unicode\u00A0spaces\u2013and\u2014dashes",
    ]
    for s in samples:
        print("IN :", s.encode("unicode_escape").decode())
        out = sanitize_for_tts(s)
        print("OUT:", out.encode("unicode_escape").decode())
        assert "\\u0327" not in out.encode("unicode_escape").decode()
    print("OK")
