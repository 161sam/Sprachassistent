#!/usr/bin/env python3
"""Check for presence of the default Piper model."""
from __future__ import annotations

from pathlib import Path

CANDIDATES = [
    Path("models/piper/de-thorsten-low.onnx"),
    Path.home() / ".local" / "share" / "piper" / "de-thorsten-low.onnx",
]


def main() -> None:
    for candidate in CANDIDATES:
        if candidate.exists():
            print(f"\u2705 Piper model found: {candidate}")
            return
    print("\u274c Piper model missing. Expected one of:")
    for c in CANDIDATES:
        print(f" - {c}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
