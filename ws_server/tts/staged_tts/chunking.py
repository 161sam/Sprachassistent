# (from upload)
"""Text-Chunking und Sanitizing für sprechgerechte TTS-Ausgabe."""
import re
from typing import List
from ws_server.tts.text_sanitizer import ( sanitize_for_tts_strict, pre_sanitize_text )
def limit_and_chunk(text: str, max_length: int = 500) -> List[str]:
    text = pre_sanitize_text(text)
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length].rsplit(' ', 1)[0]
    parts = re.split(r'(?<=[\.\!\?;:\n])\s+| — | – ', text)
    parts = [p.strip() for p in parts if p.strip()]
    chunks=[]; current=""
    for part in parts:
        if len(current)+len(part)+1 <= 180:
            current=(current+" "+part).strip()
        else:
            if current: chunks.append(current)
            current=part
    if current: chunks.append(current)
    return chunks
def create_intro_chunk(chunks: List[str], max_intro_length: int = 120) -> tuple[str, List[str]]:
    if not chunks: return "", []
    intro = chunks[0]
    if len(intro) > max_intro_length:
        intro = intro[:max_intro_length].rsplit(' ', 1)[0]
    remaining = chunks[1:] if len(chunks) > 1 else []
    if len(chunks[0]) > len(intro):
        rem = chunks[0][len(intro):].strip()
        if rem: remaining.insert(0, rem)
    return intro, remaining
def optimize_for_prosody(text: str) -> str:
    text = sanitize_for_tts_strict(text)
    number_replacements = {'20.000':'zwanzigtausend','1.000':'eintausend','2.000':'zweitausend','10.000':'zehntausend','100.000':'hunderttausend'}
    for num, word in number_replacements.items(): text = text.replace(num, word)
    text = re.sub(r'^[\-\*\+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1', text)
    text = text.replace('**','').replace('__','').replace('`','')
    text = re.sub(r'\s+',' ', text).strip()
    if text and text[-1] not in '.!?': text += '.'
    return text
