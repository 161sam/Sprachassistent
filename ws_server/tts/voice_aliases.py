from dataclasses import dataclass
from typing import Optional, Dict


@dataclass(frozen=True)
class EngineVoice:
    voice_id: Optional[str] = None
    model_path: Optional[str] = None
    language: Optional[str] = None
    sample_rate: Optional[int] = None


VOICE_ALIASES: Dict[str, Dict[str, EngineVoice]] = {
    "de-thorsten-low": {
        "piper": EngineVoice(
            model_path="models/piper/de-thorsten-low.onnx",
            language="de",
            sample_rate=22050,
        ),
        "zonos": EngineVoice(
            voice_id="thorsten",
            language="de",
            sample_rate=48000,
        ),
        # Only include kokoro mapping if you really have a German voice that matches the timbre.
        # "kokoro": EngineVoice(voice_id="de_sarah", language="de", sample_rate=24000),
    },
    # Alias with locale-style name for compatibility
    "de_DE-thorsten-low": {
        "piper": EngineVoice(
            model_path="models/piper/de-thorsten-low.onnx",
            language="de",
            sample_rate=22050,
        ),
        "zonos": EngineVoice(
            voice_id="thorsten",
            language="de",
            sample_rate=48000,
        ),
    },
}
