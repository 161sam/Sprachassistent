import os
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parent.parent))

try:
    from backend.tts.kokoro_tts_engine import KokoroTTSEngine  # type: ignore
    from backend.tts.base_tts_engine import TTSConfig  # type: ignore
except Exception as exc:  # pragma: no cover - dependency check
    raise SystemExit(f"Kokoro engine import failed: {exc}")

load_dotenv()

async def main() -> None:
    text = "Hello from Kokoro"
    model = os.getenv("KOKORO_MODEL")
    if not model or not os.path.exists(model):
        raise SystemExit("KOKORO_MODEL not configured or file missing")
    config = TTSConfig(
        engine_type="kokoro",
        model_path=model,
        voice=os.getenv("KOKORO_VOICE", "af_sarah"),
        speed=float(os.getenv("KOKORO_SPEED", "1.0")),
        language=os.getenv("KOKORO_LANG", "en"),
        sample_rate=int(os.getenv("KOKORO_SAMPLE_RATE", "24000")),
        model_dir=os.path.dirname(model) or "models",
    )
    engine = KokoroTTSEngine(config)
    init_ok = await engine.initialize()
    if not init_ok:
        raise SystemExit("Kokoro initialization failed")
    result = await engine.synthesize(text)
    if not result.success:
        raise SystemExit(f"Kokoro synthesis failed: {result.error_message}")
    if not result.audio_data:
        raise SystemExit("Kokoro returned no audio data")
    print(f"Kokoro generated {len(result.audio_data)} bytes of audio")

if __name__ == "__main__":
    asyncio.run(main())
