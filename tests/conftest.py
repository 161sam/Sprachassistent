import sys
from pathlib import Path

# Ensure project root is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Provide aiohttp's useful pytest fixtures such as ``unused_tcp_port``.
pytest_plugins = ("aiohttp.pytest_plugin",)
