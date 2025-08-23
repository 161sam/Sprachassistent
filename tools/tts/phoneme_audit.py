import json
import sys
import unicodedata
from typing import Iterable, Set

try:
    from phonemizer.backend import EspeakBackend
except Exception:  # pragma: no cover - optional dep
    EspeakBackend = None

PROBLEM_TEXTS = [
    "façade",
    "garçon",
    "çedilla",
    "fa̧cade",
    "übermäßig",
    "naïve",
    "東京",
]

def load_map(path: str) -> set[str]:
    with open(path, encoding='utf-8') as f:
        cfg = json.load(f)
    return set(cfg.get('phoneme_id_map', {}).keys())

def phonemize(texts: Iterable[str], lang: str = 'de') -> list[str]:
    if EspeakBackend is None:
        raise RuntimeError('phonemizer not available')
    be = EspeakBackend(language=lang)
    return [be.phonemize(t, strip=True) for t in texts]


def audit_texts(texts: Iterable[str], model_set: Set[str], lang: str = 'de') -> Set[str]:
    """Return set of phonemes not present in the model map."""
    outs = phonemize(texts, lang=lang)
    unknown: Set[str] = set()
    for o in outs:
        for ch in o:
            if ch and ch not in model_set and unicodedata.category(ch)[0] != 'Z':
                unknown.add(ch)
    return unknown

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: phoneme_audit.py <model.json> [lang]', file=sys.stderr)
        sys.exit(1)
    model_json = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else 'de'
    model_set = load_map(model_json)
    inputs = [line.strip() for line in sys.stdin if line.strip()]
    if not inputs:
        inputs = PROBLEM_TEXTS
    unknown = audit_texts(inputs, model_set, lang=lang)
    print('Unknown phonemes:', ' '.join(sorted(unknown)))
    for u in sorted(unknown):
        print(f"U+{ord(u):04X} {unicodedata.name(u, 'UNKNOWN')}")
