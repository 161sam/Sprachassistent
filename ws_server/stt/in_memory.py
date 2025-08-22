"""In-memory audio utilities for STT processing."""
from __future__ import annotations

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

# TODO: Streaming support for chunked STT without buffering entire audio.
