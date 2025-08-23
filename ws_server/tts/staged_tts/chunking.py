"""
Text-Chunking für sprechgerechte TTS-Ausgabe
"""

import re
import unicodedata
from typing import List

def sanitize_for_tts(text: str) -> str:
    """
    Macht Eingabetext TTS-freundlich:
    - NFC-Normalisierung
    - Zero-Width/NBSP entfernen
    - typografische Zeichen nach ASCII
    - verwaiste kombinierende Zeichen droppen
    """
    import unicodedata

    # 1) NFC
    text = unicodedata.normalize("NFC", text)

    # 2) einfache Typographie-Mappings (sichtbare Zeichen direkt)
    trans = {
        '‘': "'", '’': "'", '‚': ',', '‛': "'",
        '“': '"', '”': '"', '„': '"',
        '–': '-', '—': '-', '−': '-',
        '…': '...',
        chr(0x00A0): ' ',  # NBSP
    }
    text = text.translate(str.maketrans(trans))

    # 3) Zero-Width & Co. entfernen (per Codepoints, keine unsichtbaren Literalzeichen)
    ZW = {0x200B: None, 0x200C: None, 0x200D: None, 0x200E: None,
          0x200F: None, 0x2060: None, 0xFEFF: None}
    text = text.translate(ZW)

    # 4) Verwaiste kombinierende Zeichen entfernen
    out = []
    prev_is_base = False
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith('M') and not prev_is_base:
            # kombinierendes Zeichen ohne Basis -> verwerfen
            continue
        out.append(ch)
        prev_is_base = not cat.startswith('M')
    text = ''.join(out)

    # 5) mehrfaches Whitespace trimmen
    text = ' '.join(text.split())
    return text



def _limit_and_chunk(text: str, max_length: int = 500) -> List[str]:
    """
    Begrenze und segmentiere Text für staged TTS.
    
    Args:
        text: Eingabetext
        max_length: Maximale Gesamtlänge (Standard: 500 Zeichen)
    
    Returns:
        Liste von Text-Chunks (80-180 Zeichen pro Chunk)
    """
    try:
        text = unicodedata.normalize('NFC', text)
    except Exception:
        pass
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
    """Optimiere Text für natürliche TTS-Prosodie.

    Args:
        text: Eingabetext

    Returns:
        Optimierter Text mit besserer Zeichensetzung
    """
    text = sanitize_for_tts(text)

    # Zahlen in Wortform umwandeln (vereinfacht)
    number_replacements = {
        '20.000': 'zwanzigtausend',
        '1.000': 'eintausend',
        '2.000': 'zweitausend',
        '10.000': 'zehntausend',
        '100.000': 'hunderttausend',
    }

    # HARDCORE FIX: Cedilla und alle diakritischen Zeichen entfernen
    text = ''.join(
        char for char in unicodedata.normalize('NFD', text)
        if unicodedata.category(char) != 'Mn'
    )
    # Spezielle Behandlung für Cedilla
    text = text.replace(chr(0x0327), '')  # Combining cedilla

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
