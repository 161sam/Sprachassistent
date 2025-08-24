# --- BEGIN compat: phonemizer EspeakBackend kwarg handling ---

try:

    import inspect

    from phonemizer.backend import EspeakBackend  # type: ignore



    _sig = inspect.signature(EspeakBackend.__init__)

    if "preserve_punctuation" not in _sig.parameters:

        _orig_init = EspeakBackend.__init__



        def _patched_init(self, *args, **kwargs):

            kwargs.pop("preserve_punctuation", None)

            kwargs.pop("preserve_stress", None)

            kwargs.pop("with_stress", None)

            return _orig_init(self, *args, **kwargs)



        EspeakBackend.__init__ = _patched_init  # type: ignore[attr-defined]

except Exception:

    # still tolerant – if phonemizer missing, Zonos will error later

    pass

# --- END compat ---

"""Optional re-export of the Zonos engine."""

AVAILABLE = False
try:  # pragma: no cover - import may fail
    from backend.tts.engine_zonos import *  # type: ignore  # noqa: F401,F403
    AVAILABLE = True
except Exception as e:  # pragma: no cover
    IMPORT_ERROR = e  # exposed for diagnostics
    __all__ = []

from backend.tts.engine_zonos import ZonosTTSEngine as ZonosEngine
__all__=["ZonosTTSEngine","ZonosEngine"]
