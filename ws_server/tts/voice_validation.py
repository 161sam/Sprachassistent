from pathlib import Path
from typing import List
from .voice_aliases import VOICE_ALIASES


def validate_voice_assets(canonical_voice: str) -> List[str]:
    messages: List[str] = []
    mapping = VOICE_ALIASES.get(canonical_voice)
    if not mapping:
        return [f"❌ Voice mapping missing for '{canonical_voice}'"]

    parts: List[str] = []
    for engine in ["piper", "zonos", "kokoro"]:
        ev = mapping.get(engine)
        if not ev:
            messages.append(f"⚠️ {engine.title()} disabled for '{canonical_voice}' (no mapping)")
            continue
        if engine == "piper":
            if ev.model_path and Path(ev.model_path).exists():
                parts.append(f"Piper[{ev.model_path}]")
            else:
                messages.append(f"❌ Piper model missing: {ev.model_path}")
        else:
            if ev.voice_id:
                parts.append(f"{engine.title()}[{ev.voice_id}]")
            else:
                messages.append(
                    f"⚠️ {engine.title()} disabled for '{canonical_voice}' (missing voice_id)"
                )
    if parts:
        messages.insert(0, f"✅ Voice mapping: canonical='{canonical_voice}' → {', '.join(parts)}")
    return messages

# --- Compatibility helper for unified CLI ---
def list_voices_with_aliases():
    """Return a mapping of voice aliases to their canonical targets.

    This keeps backward compatibility with the old CLI validate command.
    """
    try:
        from . import voice_aliases as _va
        # Try common attribute names
        candidates = [
            getattr(_va, "VOICE_ALIASES", None),
            getattr(_va, "ALIASES", None),
            getattr(_va, "VOICE_MAP", None),
        ]
        for c in candidates:
            if isinstance(c, dict) and c:
                return c
        # Fallback: introspect dict-like globals
        for k, v in _va.__dict__.items():
            if k.isupper() and isinstance(v, dict):
                return v
        return {}
    except Exception:
        return {}
