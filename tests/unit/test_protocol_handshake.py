from ws_server.protocol.handshake import parse_client_hello, build_ready


def test_parse_client_hello_modern_and_legacy():
    modern = {"op": "hello", "features": {"x": 1}}
    legacy = {"type": "hello"}

    assert parse_client_hello(modern)["features"] == {"x": 1}
    assert parse_client_hello(legacy)["op"] == "hello"


def test_build_ready_features():
    msg = build_ready({"binary_audio": True})
    assert msg == {"op": "ready", "features": {"binary_audio": True}}


def test_parse_client_hello_invalid():
    try:
        parse_client_hello({"op": "nope"})
    except ValueError as exc:  # pragma: no cover - defensive branch
        assert "unexpected" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("parse_client_hello did not raise")

