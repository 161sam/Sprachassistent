#!/usr/bin/env python3
"""
Erweiterte Text-Bereinigung für TTS-Engines
Lösung für Phonem- und Zeichencodierungs-Probleme
"""

import re
import unicodedata
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)

class TTSTextSanitizer:
    """Bereinigt Text für verschiedene TTS-Engines"""
    
    def __init__(self):
        # Problematische Zeichen für Piper TTS
        self.piper_replacements = {
            # Diakritische Zeichen
            'ç': 'c',  # c mit Cedilla
            'ñ': 'n',  # n mit Tilde
            'ø': 'o',  # o mit Strich
            'æ': 'ae', # ae-Ligatur
            'œ': 'oe', # oe-Ligatur
            'ß': 'ss', # Eszett
            
            # Anführungszeichen normalisieren
            '"': '"',  # Curly quotes
            '"': '"',
            ''': "'",  # Curly apostrophe
            ''': "'",
            
            # Gedankenstriche
            '—': '-',  # Em dash
            '–': '-',  # En dash
            
            # Sonderzeichen
            '…': '...',  # Ellipse
            '€': 'Euro',
            '§': 'Paragraph',
            '©': 'Copyright',
            '®': 'Registered',
            '™': 'Trademark',
            
            # Mathematische Symbole
            '≤': 'kleiner gleich',
            '≥': 'groesser gleich',
            '≠': 'ungleich',
            '±': 'plus minus',
            
            # Arrows und Symbole
            '→': 'nach',
            '←': 'von',
            '↑': 'hoch',
            '↓': 'runter',
            '✓': 'Haken',
            '✗': 'Kreuz',
            
            # Häufige Unicode-Probleme
            '\u00A0': ' ',  # Non-breaking space
            '\u2013': '-',  # En dash
            '\u2014': '-',  # Em dash
            '\u2018': "'",  # Left single quote
            '\u2019': "'",  # Right single quote
            '\u201C': '"',  # Left double quote
            '\u201D': '"',  # Right double quote
            '\u2026': '...',# Horizontal ellipsis
            '\u00AD': '',   # Soft hyphen (remove)
        }
        
        # Zeichen, die komplett entfernt werden sollen
        self.remove_chars = {
            '\u200B',  # Zero width space
            '\u200C',  # Zero width non-joiner
            '\u200D',  # Zero width joiner
            '\uFEFF',  # Byte order mark
            '\u00AD',  # Soft hyphen
        }
        
        # Regex patterns für häufige Probleme
        self.cleanup_patterns = [
            (r'\s+', ' '),           # Multiple spaces zu einem
            (r'\.{4,}', '...'),      # Zu viele Punkte
            (r'-{2,}', '-'),         # Multiple Bindestriche
            (r'[_]{2,}', '_'),       # Multiple Underscores
            (r'\n\s*\n', '\n'),      # Leere Zeilen entfernen
        ]
    
    def sanitize_for_piper(self, text: str) -> str:
        """Bereinigt Text spezifisch für Piper TTS"""
        if not text:
            return text
        
        original_text = text
        
        try:
            # 1. Unicode normalisieren
            text = unicodedata.normalize('NFKC', text)
            
            # 2. Problematische Zeichen entfernen
            for char in self.remove_chars:
                text = text.replace(char, '')
            
            # 3. Ersetzungen anwenden
            for old_char, new_char in self.piper_replacements.items():
                text = text.replace(old_char, new_char)
            
            # 4. Diakritika entfernen (falls noch vorhanden)
            text = self._remove_diacritics(text)
            
            # 5. Cleanup-Patterns anwenden
            for pattern, replacement in self.cleanup_patterns:
                text = re.sub(pattern, replacement, text)
            
            # 6. Nur ASCII + Deutsche Umlaute beibehalten
            text = self._keep_safe_chars(text)
            
            # 7. Trimmen
            text = text.strip()
            
            if text != original_text:
                logger.debug(f"Text sanitized for Piper: '{original_text}' -> '{text}'")
            
            return text
            
        except Exception as e:
            logger.error(f"Text sanitization failed: {e}")
            # Fallback: Nur ASCII-Zeichen
            return re.sub(r'[^\x00-\x7F]+', '', original_text)
    
    def sanitize_for_zonos(self, text: str) -> str:
        """Bereinigt Text für Zonos TTS (weniger restriktiv)"""
        if not text:
            return text
        
        try:
            # Zonos ist toleranter, nur grundlegende Bereinigung
            text = unicodedata.normalize('NFKC', text)
            
            # Problematische Zero-Width-Zeichen entfernen
            for char in self.remove_chars:
                text = text.replace(char, '')
            
            # Nur grundlegende Cleanup-Patterns
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            return text
            
        except Exception as e:
            logger.error(f"Zonos text sanitization failed: {e}")
            return text
    
    def _remove_diacritics(self, text: str) -> str:
        """Entfernt diakritische Zeichen (Akzente, etc.)"""
        try:
            # Zerlege in Grundzeichen + Diakritika
            normalized = unicodedata.normalize('NFD', text)
            # Entferne nur diakritische Markierungen
            without_diacritics = ''.join(
                char for char in normalized 
                if unicodedata.category(char) != 'Mn'
            )
            return without_diacritics
        except Exception:
            return text
    
    def _keep_safe_chars(self, text: str) -> str:
        """Behält nur 'sichere' Zeichen für deutsche TTS"""
        safe_chars = set(
            'abcdefghijklmnopqrstuvwxyz'
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            'äöüÄÖÜß'  # Deutsche Umlaute
            '0123456789'
            ' .,!?;:-_()[]{}"\'/\\+'
            '\n\t'
        )
        
        return ''.join(char if char in safe_chars else ' ' for char in text)
    
    def analyze_problematic_chars(self, text: str) -> Dict:
        """Analysiert problematische Zeichen im Text"""
        if not text:
            return {}
        
        problematic = []
        unknown_unicode = []
        
        for char in text:
            if char in self.piper_replacements:
                problematic.append(char)
            elif ord(char) > 127 and char not in 'äöüÄÖÜß':
                unknown_unicode.append(char)
        
        return {
            'problematic_chars': list(set(problematic)),
            'unknown_unicode': list(set(unknown_unicode)),
            'total_chars': len(text),
            'problematic_count': len(problematic),
            'needs_sanitization': len(problematic) > 0 or len(unknown_unicode) > 0
        }

# Globale Instanz
text_sanitizer = TTSTextSanitizer()

def sanitize_for_tts(text: str, engine: str = 'piper') -> str:
    """Convenience-Funktion für Text-Bereinigung"""
    if engine.lower() == 'piper':
        return text_sanitizer.sanitize_for_piper(text)
    elif engine.lower() == 'zonos':
        return text_sanitizer.sanitize_for_zonos(text)
    else:
        # Standard: Piper-Bereinigung (restriktiver)
        return text_sanitizer.sanitize_for_piper(text)

# Test-Funktion
if __name__ == "__main__":
    # Test mit problematischen Zeichen
    test_texts = [
        "Hallo! Dies ist ein Test mit ̧ Sonderzeichen.",
        "Café, naïve, résumé, façade",
        "Das kostet 19,99€ — sehr günstig!",
        "Größer ≥ kleiner… interessant.",
        ""Anführungszeichen" und 'Apostrophe'",
        "Unicode\u00A0spaces\u2013and\u2014dashes"
    ]
    
    sanitizer = TTSTextSanitizer()
    
    for text in test_texts:
        print(f"\nOriginal: {text}")
        analysis = sanitizer.analyze_problematic_chars(text)
        print(f"Analysis: {analysis}")
        
        piper_clean = sanitizer.sanitize_for_piper(text)
        print(f"Piper:    {piper_clean}")
        
        zonos_clean = sanitizer.sanitize_for_zonos(text)
        print(f"Zonos:    {zonos_clean}")
