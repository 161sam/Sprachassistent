from __future__ import annotations
import asyncio, logging, time
from typing import Callable, Dict, Optional
from ..core.streams import AudioBuffer, AudioChunk

logger = logging.getLogger(__name__)

class AudioStreamManager:
    def __init__(self, sample_rate: int, max_duration: float,
                 on_text: Callable[[str], asyncio.Future],
                 chunk_duration_guess: float = 0.02):
        self.sample_rate = sample_rate
        self.max_duration = max_duration
        self.chunk_duration_guess = chunk_duration_guess
        self.buffers: Dict[str, AudioBuffer] = {}
        self.on_text = on_text

    async def start_stream(self, client_id: str) -> str:
        sid = f"{client_id}-{int(time.time()*1000)}"
        self.buffers[sid] = AudioBuffer(max_duration_s=self.max_duration)
        return sid

    async def push_chunk(self, stream_id: str, pcm16: bytes) -> None:
        buf = self.buffers.get(stream_id)
        if not buf: return
        buf.push(AudioChunk(pcm16=pcm16, timestamp=time.time(), duration_s=self.chunk_duration_guess))

    async def end_stream(self, stream_id: str) -> Optional[str]:
        buf = self.buffers.pop(stream_id, None)
        if not buf: return None
        data = buf.pop_all()
        # Übergibt an die Sprachverarbeitung (STT+LLM+TTS orchestration außerhalb)
        # Rückgabe: erkannter Text (optional)
        # (Die konkrete Orchestrierung implementiert VoiceServer)
        return data
