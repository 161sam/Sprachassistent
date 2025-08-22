"""Audio stream helpers."""

from dataclasses import dataclass
from typing import Iterable


@dataclass
class AudioStream:
    samples: Iterable[int]


__all__ = ["AudioStream"]
