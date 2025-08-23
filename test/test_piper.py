import os
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure repository root on path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from ws_server.tts.engines.piper import PiperTTSEngine  # type: ignore
from backend.tts.base_tts_engine import TTSConfig  # type: ignore

load_dotenv()

async def main() -> None:
    text = "Hallo Welt"
    model = os.getenv("PIPER_MODEL")
    if not model or not os.path.exists(model):
        raise SystemExit("PIPER_MODEL not configured or file missing")
    config = TTSConfig(
        engine_type="piper",
        model_path=model,
        voice=os.getenv("PIPER_VOICE", "de-thorsten-low"),
        speed=float(os.getenv("PIPER_SPEED", "1.0")),
        language=os.getenv("PIPER_LANG", "de"),
        sample_rate=int(os.getenv("PIPER_SAMPLE_RATE", "22050")),
        model_dir=os.path.dirname(model) or "models",
    )
    engine = PiperTTSEngine(config)
    init_ok = await engine.initialize()
    if not init_ok:
        raise SystemExit("Piper initialization failed")
    result = await engine.synthesize(text)
    if not result.success:
        raise SystemExit(f"Piper synthesis failed: {result.error_message}")
    if not result.audio_data:
        raise SystemExit("Piper returned no audio data")
    print(f"Piper generated {len(result.audio_data)} bytes of audio")

if __name__ == "__main__":
    asyncio.run(main())
