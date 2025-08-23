"""Voice alias configuration loader."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

# TODO-FIXED(2025-08-23): unified with config/tts.json and environment defaults

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "tts.json"


def _load_jsonc(path: Path) -> Dict[str, object]:
    """Load JSON with // comment stripping."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"//.*", "", text)
    return json.loads(text)


@dataclass(frozen=True)
class EngineVoice:
    voice_id: Optional[str] = None
    model_path: Optional[str] = None
    language: Optional[str] = None
    sample_rate: Optional[int] = None


def _build_aliases() -> Dict[str, Dict[str, EngineVoice]]:
    data = _load_jsonc(CONFIG_PATH)
    result: Dict[str, Dict[str, EngineVoice]] = {}
    for alias, engines in data.get("voice_map", {}).items():
        result[alias] = {eng: EngineVoice(**cfg) for eng, cfg in engines.items()}
    return result


VOICE_ALIASES: Dict[str, Dict[str, EngineVoice]] = _build_aliases()

__all__ = ["VOICE_ALIASES", "EngineVoice"]
