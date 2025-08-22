"""Common utilities for tests."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ws_server.core.config import load_env as _load_env


class BaseTest:
    """Base test class providing environment loading utilities."""

    @staticmethod
    def load_env(profile: Optional[str] = None) -> None:
        """Load environment variables from ``.env`` files.

        Parameters
        ----------
        profile:
            Optional profile name, e.g. ``all-in-one-pi``.
        """

        env_file = Path(f".env.{profile}") if profile else Path(".env")
        _load_env(env_file if env_file.exists() else None)
