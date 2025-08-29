#!/usr/bin/env python3
"""Terminal progress rendering for staged TTS (intro/main).

- Single-line updates with carriage return when TTY is present
- Fallback to compact multi-line logs when not a TTY
- Throttled to avoid log spam
"""
from __future__ import annotations

import os
import sys
import time
import json
import shutil
from pathlib import Path

_BOOL_TRUE = {"1", "true", "yes", "on"}


def _load_terminal_progress_default() -> bool:
    """Read default from tts_defaults.json if available, else True.

    Env var TTS_PROGRESS overrides JSON.
    """
    env = os.getenv("TTS_PROGRESS")
    if env is not None:
        return str(env).strip().lower() in _BOOL_TRUE

    # Try repo config JSON
    try:
        here = Path(__file__).resolve()
        repo_root = here.parents[4] if len(here.parents) >= 5 else here.parents[-1]
        candidates = [
            repo_root / "ws_server" / "config" / "tts_defaults.json",
            repo_root / "config" / "tts_defaults.json",
        ]
        for p in candidates:
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                val = data.get("terminal_progress")
                if isinstance(val, bool):
                    return val
                break
    except Exception:
        pass
    # Default to True for development friendliness
    return True


def progress_enabled() -> bool:
    return _load_terminal_progress_default()


class ProgressRenderer:
    def __init__(self, label: str, total: int, enabled: bool = True):
        self.label = (label or "").strip() or "progress"
        self.total = max(1, int(total or 1))
        self._want = bool(enabled)
        # track whether we're on a real terminal
        try:
            self._tty = bool(sys.stderr.isatty())
        except Exception:
            self._tty = False
        self._last_ratio = -1.0
        self._last_print = 0.0
        self._last_step = -1

    def _bar(self, ratio: float, width: int) -> str:
        width = max(10, int(width))
        fill = int(width * ratio)
        # ASCII fallback characters if unicode not supported are still fine in most terms
        return "█" * fill + "░" * (width - fill)

    def update(self, current: int):
        if not self._want:
            return
        # Bound current
        current = max(0, min(int(current), self.total))
        ratio = min(1.0, max(0.0, (current / float(self.total)) if self.total else 0.0))
        now = time.time()

        # Throttle: only if percent changed or >50ms elapsed
        pct_now = int(ratio * 100)
        pct_last = int(self._last_ratio * 100)
        if (pct_now == pct_last) and ((now - self._last_print) < 0.05):
            return

        self._last_ratio = ratio
        self._last_print = now
        try:
            cols = shutil.get_terminal_size((80, 20)).columns
        except Exception:
            cols = 80
        bar_w = max(14, min(40, cols - 40))
        bar = self._bar(ratio, bar_w)
        pct = int(ratio * 100)
        # label format: 5 chars left-justified + ':' to match examples:
        # 'intro:' and 'main :' -> f"{name.ljust(5)}:"
        lbl = f"{self.label.ljust(5)}:"
        msg = f"{lbl} [{bar}] {pct:3d}% ({current}/{self.total})"

        if self._tty:
            try:
                sys.stderr.write("\r" + msg)
                sys.stderr.flush()
            except Exception:
                pass
        else:
            # Non-TTY: log once per step progression to avoid flooding
            step = current
            if step != self._last_step:
                self._last_step = step
                try:
                    sys.stderr.write(msg + "\n")
                    sys.stderr.flush()
                except Exception:
                    pass

    def done(self):
        if not self._want:
            return
        if self._tty:
            try:
                cols = shutil.get_terminal_size((80, 20)).columns
            except Exception:
                cols = 80
            try:
                sys.stderr.write("\r" + (" " * cols) + "\r")
                sys.stderr.flush()
            except Exception:
                pass


__all__ = ["ProgressRenderer", "progress_enabled"]
