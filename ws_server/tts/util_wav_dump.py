from __future__ import annotations

import wave
import os

def write_wav_mono_int16(path: str, pcm16: bytes, sample_rate: int) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sample_rate or 22050))
        wf.writeframes(pcm16 or b"")

__all__ = ["write_wav_mono_int16"]
