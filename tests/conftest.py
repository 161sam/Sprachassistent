import sys
from pathlib import Path
import pytest

# Ensure project root is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Provide aiohttp's useful pytest fixtures and enable ``pytest-asyncio``.
pytest_plugins = ("aiohttp.pytest_plugin", "pytest_asyncio")


@pytest.fixture
def unused_tcp_port(unused_port) -> int:
    """Compat shim for older fixture name.

    ``aiohttp.pytest_plugin`` exposes ``unused_port`` as a callable fixture
    returning a free port.  This alias mimics ``unused_tcp_port`` by invoking
    that callable.
    """

    return unused_port()
