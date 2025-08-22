"""
Text-Chunking für sprechgerechte TTS-Ausgabe
"""

import re
from typing import List


def _limit_and_chunk(text: str, max_length: int = 500) -> List[str]:
    """
    Begrenze und segmentiere Text für staged TTS.
    
    Args:
        text: Eingabetext
        max_length: Maximale Gesamtlänge (Standard: 500 Zeichen)
    
    Returns:
        Liste von Text-Chunks (80-180 Zeichen pro Chunk)
    """
    # Text begrenzen auf max_length
    text = text.strip()
    if len(text) > max_length:
        # An Wortgrenze abschneiden
        text = text[:max_length].rsplit(' ', 1)[0]
    
    # Satz-Segmentierung nach Punkt, Semikolon, Doppelpunkt, Gedankenstrich
    parts = re.split(r'(?<=[\.\!\?;:\n])\s+| — | – ', text)
    parts = [p.strip() for p in parts if p.strip()]
    
    # Kleine Parts zusammenführen, damit 80–180 Zeichen erreicht werden
    chunks = []
    current_chunk = ""
    
    for part in parts:
        # Prüfe ob current_chunk + part noch unter 180 Zeichen ist
        if len(current_chunk) + len(part) + 1 <= 180:
            current_chunk = (current_chunk + " " + part).strip()
        else:
            # Current chunk ist voll, speichere ihn
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = part
    
    # Letzten Chunk hinzufügen
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def create_intro_chunk(chunks: List[str], max_intro_length: int = 120) -> tuple[str, List[str]]:
    """
    Erstelle Intro-Chunk für Piper (Stage A) und Rest für Zonos (Stage B).
    
    Args:
        chunks: Liste aller Text-Chunks
        max_intro_length: Maximale Länge des Intro-Chunks
    
    Returns:
        Tuple von (intro_text, remaining_chunks)
    """
    if not chunks:
        return "", []
    
    # Ersten Chunk als Intro verwenden, ggf. kürzen
    intro = chunks[0]
    if len(intro) > max_intro_length:
        # Am letzten Wort vor max_intro_length abschneiden
        intro = intro[:max_intro_length].rsplit(' ', 1)[0]
    
    # Rest der Chunks für Zonos
    remaining = chunks[1:] if len(chunks) > 1 else []
    
    # Falls der erste Chunk gekürzt wurde, den Rest als neuen Chunk hinzufügen
    if len(chunks[0]) > len(intro):
        remainder = chunks[0][len(intro):].strip()
        if remainder:
            remaining.insert(0, remainder)
    
    return intro, remaining


def optimize_for_prosody(text: str) -> str:
    """
    Optimiere Text für natürliche TTS-Prosodie.
    
    Args:
        text: Eingabetext
    
    Returns:
        Optimierter Text mit besserer Zeichensetzung
    """
    # Zahlen in Wortform umwandeln (vereinfacht)
    number_replacements = {
        '20.000': 'zwanzigtausend',
        '1.000': 'eintausend',
        '2.000': 'zweitausend',
        '10.000': 'zehntausend',
        '100.000': 'hunderttausend',
    }
    
    result = text
    for num, word in number_replacements.items():
        result = result.replace(num, word)

    # Entferne einfache Markdown-Listen und Formatierungen
    result = re.sub(r'^[\-\*\+]\s+', '', result, flags=re.MULTILINE)
    result = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1', result)
    result = result.replace('**', '').replace('__', '').replace('`', '')

    # Entferne redundante Leerzeichen
    result = re.sub(r'\s+', ' ', result)
    
    # Stelle sicher, dass Sätze mit Punkt enden
    result = result.strip()
    if result and result[-1] not in '.!?':
        result += '.'
    
    return result
