from ws_server.protocol.binary_v2 import build_audio_frame, parse_audio_frame


def test_roundtrip_parsing():
    audio = b"\x00\x01\x02"
    frame_bytes = build_audio_frame("stream", 5, 1234.5, audio)
    frame = parse_audio_frame(frame_bytes)
    assert frame.stream_id == "stream"
    assert frame.sequence == 5
    assert frame.timestamp == 1234.5
    assert frame.audio_data == audio


def test_too_short_frame():
    short = b"\x00"  # clearly too short
    try:
        parse_audio_frame(short)
    except ValueError as exc:
        assert "too short" in str(exc)
    else:
        raise AssertionError("parse_audio_frame did not raise ValueError")
