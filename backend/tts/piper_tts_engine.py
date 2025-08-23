"""Deprecated wrapper for the Piper engine.

The Piper implementation now lives in :mod:`ws_server.tts.engines.piper`.
This module re-exports the class for backwards compatibility and informs
developers about the new import path.
"""

from __future__ import annotations

from ws_server.tts.engines.piper import PiperTTSEngine

__all__ = ["PiperTTSEngine"]

