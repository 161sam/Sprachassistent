import os
import unicodedata
import re
import logging

logger = logging.getLogger(__name__)

ZERO_WIDTH = dict.fromkeys(map(ord, "\u200B\u200C\u200D\u200E\u200F\u2060\uFEFF"), None)
TYPO_MAP = {
    '‘': "'", '’': "'", '‚': ',', '‛': "'",
    '“': '"', '”': '"', '„': '"',
    '–': '-', '—': '-', '−': '-',
    '…': '...',
    '\u00A0': ' ',
    'ç': 'c', 'Ç': 'C',
}
_warned: set[str] = set()

def _warn_once(ch: str, reason: str) -> None:
    if ch not in _warned:
        logger.warning("Entferne Zeichen %r wegen %s (U+%04X)", ch, reason, ord(ch))
        _warned.add(ch)

def sanitize_for_tts(text: str, mode: str | None = None) -> str:
    if os.getenv("TTS_SANITIZE_ENABLED", "true").lower() != "true":
        return text
    norm = os.getenv("TTS_UNICODE_NORMALIZATION", "NFC").upper()
    if norm not in {"NFC", "NFKC"}:
        norm = "NFC"
    if mode == "aggressive":
        norm = "NFKC"
    text = unicodedata.normalize(norm, text)
    text = text.translate(str.maketrans(TYPO_MAP))
    text = text.translate(ZERO_WIDTH)
    drop_orphans = os.getenv("TTS_DROP_ORPHAN_COMBINING", "true").lower() == "true"
    out: list[str] = []
    for ch in text:
        cat = unicodedata.category(ch)
        if drop_orphans and cat == 'Mn':
            _warn_once(ch, "kombinierende Markierung entfernt")
            continue
        out.append(ch)
    text = ''.join(out)
    text = re.sub(r"\s+", " ", text).strip()
    return text
