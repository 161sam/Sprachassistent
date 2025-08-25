from importlib import import_module
from typing import Any, Callable, Dict, Tuple
from ws_server.tts.exceptions import EngineUnavailable

# Engine-Name -> ("modulpfad", "Klassenname")
REGISTRY: Dict[str, Tuple[str, str]] = {
    'piper':  ('ws_server.tts.engines.piper',  'PiperTTSEngine'),
    'kokoro': ('ws_server.tts.engines.kokoro', 'KokoroTTSEngine'),
    'zonos':  ('ws_server.tts.engines.zonos',  'ZonosTTSEngine'),
}

def available_engines() -> Dict[str, Tuple[str, str]]:
    return dict(REGISTRY)

def load_engine(name: str) -> Callable[..., Any]:
    """Lazy-Import der gewünschten Engine-Klasse."""
    try:
        module_path, class_name = REGISTRY[name]
    except KeyError as e:
        raise EngineUnavailable(f"Unbekannte Engine: {name!r}") from e

    try:
        mod = import_module(module_path)
        cls = getattr(mod, class_name)
        return cls
    except Exception as e:
        raise EngineUnavailable(
            f"Engine '{name}' ist nicht verfügbar (Importfehler: {e})."
        ) from e
