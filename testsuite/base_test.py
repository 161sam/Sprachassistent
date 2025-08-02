"""Common utilities for tests."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

class BaseTest:
    """Base test class providing environment loading utilities."""

    @staticmethod
    def load_env(profile: Optional[str] = None) -> None:
        """Load environment variables from .env files.

        Parameters
        ----------
        profile: optional str
            Name of the profile to load, e.g. ``all-in-one-pi``.
        """
        env_file = Path(".env.defaults")
        if profile:
            candidate = Path(f".env.{profile}")
            if candidate.exists():
                env_file = candidate
        load_dotenv(env_file, override=True)
