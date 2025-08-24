"""Utilities for validating local TTS model assets."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


def _check_file(path: Path) -> bool:
    """Prüfe Datei und warne bei fehlenden oder defekten Symlinks."""
    if path.is_symlink() and not path.exists():
        logger.warning("Defekter Symlink: %s -> %s", path, os.readlink(path))
        logger.info("💡 Beheben mit: ln -sf <Ziel> %s", path)
        return False
    if not path.is_file():
        logger.warning("Fehlende Datei: %s", path)
        return False
    return True


def _resolve_models_base(base_dir: str | None = None) -> Path:
    """Return base directory for TTS models."""
    if base_dir:
        return Path(base_dir)
    env = os.getenv("TTS_MODEL_DIR") or os.getenv("MODELS_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "models"


def validate_models(base_dir: str | None = None) -> List[str]:
    """Validate model files and return list of available voices."""
    base = _resolve_models_base(base_dir)
    piper_dir = base / "piper"
    voices: List[str] = []
    if not piper_dir.exists():
        logger.warning("Modellverzeichnis fehlt: %s", piper_dir)
        return voices

    for onnx_file in sorted(piper_dir.glob("*.onnx")):
        json_file = Path(str(onnx_file) + ".json")
        _check_file(onnx_file)
        _check_file(json_file)
        voices.append(onnx_file.stem)

    for json_file in piper_dir.glob("*.onnx.json"):
        onnx_file = Path(str(json_file)[:-5])  # remove trailing '.json'
        _check_file(json_file)
        if not onnx_file.exists():
            logger.warning("Konfigurationsdatei ohne Modell: %s", json_file)

    return voices


def list_voices_with_aliases(base_dir: str | None = None) -> Dict[str, List[str]]:
    """Return mapping of canonical voices to their aliases."""
    voices = validate_models(base_dir)
    alias_map: Dict[str, List[str]] = {v: [] for v in voices}

    try:
        import importlib.util

        va_path = Path(__file__).with_name("voice_aliases.py")
        spec = importlib.util.spec_from_file_location("voice_aliases", va_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)  # type: ignore[assignment]
        voice_aliases = getattr(module, "VOICE_ALIASES", {})
    except Exception:  # pragma: no cover - fallback if file missing
        voice_aliases = {}

    for alias, canonical in voice_aliases.items():
        if canonical in alias_map and alias != canonical:
            alias_map[canonical].append(alias)
    return alias_map

