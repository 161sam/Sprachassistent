import os
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'token_utils',
    Path(__file__).resolve().parents[1] / 'backend/ws-server/auth/token_utils.py'
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
verify_token = module.verify_token


def test_verify_token_plain(monkeypatch):
    monkeypatch.setenv('JWT_ALLOW_PLAIN', '1')
    monkeypatch.setenv('JWT_BYPASS', '0')
    monkeypatch.setenv('JWT_SECRET', 'devsecret')
    assert verify_token('devsecret') is True


def test_verify_token_bypass_allows_empty(monkeypatch):
    monkeypatch.setenv('JWT_BYPASS', '1')
    monkeypatch.setenv('JWT_ALLOW_PLAIN', '0')
    assert verify_token(None) is True
