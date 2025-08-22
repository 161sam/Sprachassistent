"""Compatibility alias for legacy `audio` imports.

This package mirrors `ws_server.audio` so that older modules
expecting `audio.vad` continue to function.
"""

from ws_server.audio import *  # noqa: F401,F403
