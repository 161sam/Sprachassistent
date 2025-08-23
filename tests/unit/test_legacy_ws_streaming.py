import sys
import types
import pytest

# Provide minimal stubs for heavy optional dependencies during import
fw = types.ModuleType("faster_whisper")
fw.WhisperModel = object  # type: ignore[attr-defined]
sys.modules.setdefault("faster_whisper", fw)

dotenv_mod = types.ModuleType("dotenv")
dotenv_mod.load_dotenv = lambda *a, **k: None
sys.modules.setdefault("dotenv", dotenv_mod)

from ws_server.compat.legacy_ws_server import AsyncSTTEngine  # noqa: E402


class _DummySTT(AsyncSTTEngine):
    async def transcribe_audio(self, audio_data: bytes) -> str:  # pragma: no cover - simple stub
        return str(len(audio_data))


@pytest.mark.asyncio
async def test_process_binary_audio_streams_chunks_individually():
    stt = _DummySTT()
    chunk_a = b"\x00\x00" * 10
    chunk_b = b"\x01\x00" * 5

    res_a = await stt.process_binary_audio(chunk_a, stream_id="s", sequence=0)
    res_b = await stt.process_binary_audio(chunk_b, stream_id="s", sequence=1)

    assert res_a == {"text": "20"}
    assert res_b == {"text": "10"}
