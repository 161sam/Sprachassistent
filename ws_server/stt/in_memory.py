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
