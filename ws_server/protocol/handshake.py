"""Protocol negotiation helpers."""

from __future__ import annotations
from typing import Any, Dict


def parse_client_hello(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize client hello payload.

    Supports both the modern ``{"op": "hello"}`` format and the legacy
    ``{"type": "hello"}`` variant.

    Returns a normalized mapping with an ``op`` field set to ``"hello"`` and
    a ``features`` dictionary.
    """

    op = data.get("op") or data.get("type")
    if op != "hello":  # pragma: no cover - defensive
        raise ValueError("unexpected handshake op")
    return {"op": "hello", "features": data.get("features", {})}


def build_ready(features: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return a ready message for handshake replies."""
    return {"op": "ready", "features": features or {}}


__all__ = ["parse_client_hello", "build_ready"]
