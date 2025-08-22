from ws_server.core.config import Config
from ws_server.auth import token as token_module


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("WS_HOST", "0.0.0.0")
    monkeypatch.setenv("WS_PORT", "9999")
    cfg = Config.from_env()
    assert cfg.ws_host == "0.0.0.0"
    assert cfg.ws_port == 9999


def test_verify_token_respects_config(monkeypatch):
    cfg = Config.from_env()
    cfg.jwt_bypass = False
    cfg.jwt_allow_plain = True
    cfg.jwt_secret = "s3cr3t"
    monkeypatch.setattr(token_module, "config", cfg)
    assert token_module.verify_token("s3cr3t")
    assert not token_module.verify_token("wrong")
