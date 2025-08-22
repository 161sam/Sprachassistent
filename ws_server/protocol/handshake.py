"""Protocol negotiation helpers."""

from __future__ import annotations
from typing import Any, Dict


def build_ready(features: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return a ready message for handshake replies."""
    return {"op": "ready", "features": features or {}}


__all__ = ["build_ready"]
