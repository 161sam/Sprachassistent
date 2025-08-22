"""JSON based message helpers (protocol v1)."""

from __future__ import annotations
from typing import Any, Dict


def parse_message(data: str) -> Dict[str, Any]:
    """Parse a JSON string into a dictionary."""
    import json
    return json.loads(data)


__all__ = ["parse_message"]
