"""In-memory audio utilities for STT processing."""
from __future__ import annotations

from typing import Iterable, Iterator

import numpy as np


def bytes_to_int16(data: bytes) -> np.ndarray:
    """Convert little-endian PCM16 bytes to a NumPy int16 array."""
    return np.frombuffer(data, dtype=np.int16)


def pcm16_bytes_to_float32(data: bytes) -> np.ndarray:
    """Convert PCM16 bytes to a normalized float32 NumPy array.

    Args:
        data: Raw little-endian PCM16 audio bytes.

    Returns:
        np.ndarray: Normalized float32 samples in range [-1.0, 1.0].
    """
    samples = bytes_to_int16(data).astype(np.float32)
    samples /= 32768.0
    return samples


def iter_pcm16_stream(chunks: Iterable[bytes]) -> Iterator[np.ndarray]:
    """Yield float32 sample arrays for a stream of PCM16 byte chunks.

    The generator keeps leftover bytes between iterations so that samples
    are only produced when a full 16-bit frame is available. This allows
    streaming STT pipelines to process audio incrementally without
    buffering the entire payload.
    """
    buffer = bytearray()
    for chunk in chunks:
        if not chunk:
            continue
        buffer.extend(chunk)
        # only convert full samples (2 bytes per int16)
        length = len(buffer) - (len(buffer) % 2)
        if length:
            yield pcm16_bytes_to_float32(bytes(buffer[:length]))
            del buffer[:length]
    # leftover byte (if any) is discarded silently; it cannot form a sample


import asyncio, logging
from typing import Optional

logger = logging.getLogger(__name__)

class AsyncSTTEngine:
    def __init__(self, model_size: str="tiny", model_path: Optional[str]=None, device: str="cpu", workers: int=1):
        self.model_size = model_size
        self.model_path = model_path
        self.device = device
        self.workers = workers
        self._model = None

    async def initialize(self) -> None:
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self.model_path or self.model_size, device=self.device, compute_type="int8" if self.device=="cpu" else "float16", num_workers=self.workers)
        except Exception as e:
            logger.warning("STT init failed: %s (falling back to None)", e)
            self._model = None

    async def transcribe_audio(self, pcm16: bytes, sample_rate: int=16000) -> str:
        if not self._model or not pcm16:
            return ""
        from numpy import frombuffer, int16
        import numpy as np
        audio = frombuffer(pcm16, dtype=int16).astype("float32") / 32768.0
        segments, info = await asyncio.get_event_loop().run_in_executor(None, lambda: list(self._model.transcribe(audio, vad_filter=True)))
        text = " ".join((s.text or "").strip() for s in segments if getattr(s, "text", ""))
        return text.strip()
