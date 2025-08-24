"""Runtime voice alias expansion for TTS engines.

- Keep ONLY canonical keys in config/tts.json (e.g. "de-thorsten-low").
- Locale-style aliases (e.g. "de_DE-thorsten-low") are generated at runtime.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional
import json as _json
from pathlib import Path as _Path

# Public API expected by TTSManager
@dataclass
class EngineVoice:
    model_path: Optional[str] = None
    voice_id: Optional[str] = None
    language: Optional[str] = None
    sample_rate: Optional[int] = None

# VOICE_ALIASES structure:
# { "<canonical-voice>": { "piper": EngineVoice(...), "zonos": EngineVoice(...), ... } }
VOICE_ALIASES: Dict[str, Dict[str, EngineVoice]] = {}

def _canonicalize_voice(v: str | None) -> str | None:
    if not v:
        return v
    return v.strip().replace("de_DE-", "de-")

def _expand_aliases(vm: Dict[str, Dict[str, EngineVoice]]) -> Dict[str, Dict[str, EngineVoice]]:
    """Create locale-style aliases (e.g. de_DE-…) in memory, without duplicating JSON."""
    out = dict(vm)
    for key, engines in list(vm.items()):
        if key.startswith("de-"):
            alias = key.replace("de-", "de_DE-")
            out.setdefault(alias, engines)
    return out

def _load_config_map() -> Dict[str, Dict[str, EngineVoice]]:
    cfg = _Path(__file__).resolve().parents[2] / "config" / "tts.json"
    data = _json.loads(cfg.read_text(encoding="utf-8"))
    vmap = data.get("voice_map", {})
    resolved: Dict[str, Dict[str, EngineVoice]] = {}
    for canonical, engs in vmap.items():
        c = _canonicalize_voice(canonical) or canonical
        resolved[c] = {}
        for engine, params in (engs or {}).items():
            resolved[c][engine] = EngineVoice(
                model_path=params.get("model_path"),
                voice_id=params.get("voice_id"),
                language=params.get("language"),
                sample_rate=params.get("sample_rate"),
            )
    return resolved

# Build mapping once at import
try:
    _base = _load_config_map()
    VOICE_ALIASES = _expand_aliases(_base)
except Exception:  # pragma: no cover
    VOICE_ALIASES = {}
