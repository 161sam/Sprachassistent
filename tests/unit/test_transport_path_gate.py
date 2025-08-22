import importlib
import sys
import types
import pytest


def _stub_compat():
    stub = types.SimpleNamespace(VoiceServer=object)
    sys.modules["ws_server.compat.legacy_ws_server"] = stub


def test_blocks_legacy_module(monkeypatch):
    _stub_compat()
    sys.modules.pop("ws_server.transport.server", None)
    fake = types.ModuleType("backend.ws_server.fake")
    fake.__file__ = "/tmp/backend/ws-server/fake.py"
    sys.modules["backend.ws_server.fake"] = fake
    with pytest.raises(RuntimeError):
        importlib.import_module("ws_server.transport.server")
    sys.modules.pop("backend.ws_server.fake", None)
    sys.modules.pop("ws_server.transport.server", None)
    sys.modules.pop("ws_server.compat.legacy_ws_server", None)


def test_import_ok_without_legacy(monkeypatch):
    _stub_compat()
    sys.modules.pop("ws_server.transport.server", None)
    importlib.import_module("ws_server.transport.server")
    sys.modules.pop("ws_server.transport.server", None)
    sys.modules.pop("ws_server.compat.legacy_ws_server", None)
