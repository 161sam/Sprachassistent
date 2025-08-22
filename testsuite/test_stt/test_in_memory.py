import numpy as np

from ws_server.stt import bytes_to_int16, pcm16_bytes_to_float32


def test_bytes_to_int16_roundtrip():
    orig = np.array([0, 32767, -32768], dtype=np.int16)
    data = orig.tobytes()
    restored = bytes_to_int16(data)
    assert restored.dtype == np.int16
    assert np.array_equal(restored, orig)


def test_pcm16_bytes_to_float32_range():
    orig = np.array([0, 32767, -32768], dtype=np.int16)
    data = orig.tobytes()
    floats = pcm16_bytes_to_float32(data)
    assert floats.dtype == np.float32
    assert floats[1] > 0.99
    assert floats[2] <= -1.0
