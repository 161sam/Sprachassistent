"""Light-weight Zonos stub used during tests.

This module provides a minimal drop-in replacement for the real Zonos
library so that the TTS engine can run inside the test suite without
pulling the heavyweight model dependencies.  Only the methods exercised
by the tests are implemented and they intentionally return simple dummy
values.
"""

from __future__ import annotations

import torch


class _DummyAutoencoder:
    """Very small stand‑in for the real autoencoder component."""

    sampling_rate = 44100

    def decode(self, codes: torch.Tensor) -> torch.Tensor:
        """Return silent audio for the given batch size."""
        batch = getattr(codes, "shape", [1])[0] or 1
        return torch.zeros(batch, 1, 10)


class Zonos:
    """Stubbed Zonos model with the minimal API used by the engine."""

    def __init__(self) -> None:
        self.autoencoder = _DummyAutoencoder()

    @staticmethod
    def from_pretrained(model_id: str, device: str = "cpu") -> "Zonos":
        return Zonos()

    # ------------------------------------------------------------------
    # Methods mirrored from the real model
    # ------------------------------------------------------------------
    def prepare_conditioning(self, cond_dict):
        return cond_dict

    def generate(self, conditioning):
        return torch.zeros(1, 10)

    def make_speaker_embedding(self, wav, sr):
        return torch.zeros(1)

    def parameters(self):
        yield torch.zeros(1)
