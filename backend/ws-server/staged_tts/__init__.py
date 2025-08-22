"""
Staged TTS Module für verbesserte Benutzererfahrung

Implementiert das zweistufige TTS-System:
- Stage A: Piper (CPU, schneller Intro ≤120 Zeichen)
- Stage B: Zonos (GPU, hochwertiger Hauptinhalt)
"""

from .chunking import limit_and_chunk
from .staged_processor import StagedTTSProcessor

__all__ = ['limit_and_chunk', 'StagedTTSProcessor']
