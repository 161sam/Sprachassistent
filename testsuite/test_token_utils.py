from ws_server.auth.token import verify_token


def test_verify_token_plain(monkeypatch):
    monkeypatch.setenv('JWT_ALLOW_PLAIN', '1')
    monkeypatch.setenv('JWT_BYPASS', '0')
    monkeypatch.setenv('JWT_SECRET', 'devsecret')
    assert verify_token('devsecret') is True


def test_verify_token_bypass_allows_empty(monkeypatch):
    monkeypatch.setenv('JWT_BYPASS', '1')
    monkeypatch.setenv('JWT_ALLOW_PLAIN', '0')
    assert verify_token(None) is True
