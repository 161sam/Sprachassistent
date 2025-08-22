"""Connection management utilities."""

from dataclasses import dataclass


@dataclass
class ConnectionStats:
    active: int = 0
    total: int = 0


__all__ = ["ConnectionStats"]
