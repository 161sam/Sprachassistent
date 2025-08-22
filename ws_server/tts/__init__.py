"""Text-to-Speech utilities and engine exports."""

try:  # pragma: no cover - optional dependencies may be missing
    from .manager import TTSManager, TTSConfig, TTSEngineType
    __all__ = ["TTSManager", "TTSConfig", "TTSEngineType"]
except Exception:  # pragma: no cover - expose empty API if manager unavailable
    __all__: list[str] = []
