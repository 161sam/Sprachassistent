import asyncio
import time

from ws_server.tts.staged_tts.staged_processor import (
    StagedTTSConfig,
    StagedTTSProcessor,
)


class MockTTSManager:
    async def synthesize(self, text, engine=None):
        await asyncio.sleep(0.01 if engine == "piper" else 0.02)

        class Result:
            success = True
            audio_data = b"mock"
            engine_used = engine
            error_message = None

        return Result()


def test_staged_tts_flow():
    """Ensure staged TTS returns intro and main chunks with sequence end."""
    processor = StagedTTSProcessor(MockTTSManager(), StagedTTSConfig())
    start = time.time()
    chunks = asyncio.run(
        processor.process_staged_tts(
            "Hallo Welt. Dies ist ein Test fuer das Staged TTS System."
        )
    )
    duration = time.time() - start
    assert duration < 1.0
    assert chunks
    assert chunks[0].engine == "piper"
    messages = [processor.create_chunk_message(c) for c in chunks]
    messages.append(processor.create_sequence_end_message(chunks[0].sequence_id))
    assert messages[0]["type"] == "tts_chunk"
    assert messages[-1]["type"] == "tts_sequence_end"
