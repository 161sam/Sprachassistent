"""Audio stream helpers."""

from dataclasses import dataclass
from typing import Iterable


@dataclass
class AudioStream:
    samples: Iterable[int]


__all__ = ["AudioStream"]


# --- Added by migration: basic audio chunk/buffer types ---
from dataclasses import dataclass, field
from typing import Deque, Optional, Callable
from collections import deque
import time

@dataclass
class AudioChunk:
    pcm16: bytes
    timestamp: float
    duration_s: float

class AudioBuffer:
    def __init__(self, max_duration_s: float = 10.0):
        self._q: Deque[AudioChunk] = deque()
        self._dur: float = 0.0
        self._max = max_duration_s
    def push(self, ch: AudioChunk) -> None:
        self._q.append(ch); self._dur += ch.duration_s
        while self._dur > self._max and self._q:
            old = self._q.popleft(); self._dur -= old.duration_s
    def clear(self) -> None:
        self._q.clear(); self._dur = 0.0
    def pop_all(self) -> bytes:
        out = b""
        while self._q:
            out += self._q.popleft().pcm16
        self._dur = 0.0
        return out
