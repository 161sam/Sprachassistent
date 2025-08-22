import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "ws-server"))
from staged_tts.staged_processor import StagedTTSProcessor, StagedTTSConfig


class OnlyPiperManager:
    engines = {"piper": object()}

    async def synthesize(self, text, engine=None):
        if engine != "piper":
            raise ValueError("engine not available")
        class R:
            success = True
            audio_data = b"x"
            engine_used = engine
            error_message = None
        await asyncio.sleep(0)
        return R()


def test_fallback_to_piper_only():
    proc = StagedTTSProcessor(OnlyPiperManager(), StagedTTSConfig(max_chunks=3))
    chunks = asyncio.run(proc.process_staged_tts("Hallo Welt. Noch ein Satz."))
    assert len(chunks) == 1
    assert chunks[0].engine == "piper"
