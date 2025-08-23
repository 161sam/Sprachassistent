import numpy as np

from ws_server.stt import iter_pcm16_stream, pcm16_bytes_to_float32


def test_iter_pcm16_stream_handles_partial_chunks():
    orig = np.array([0, 32767, -32768], dtype=np.int16)
    data = orig.tobytes()
    # split into irregular chunk sizes to test buffering
    chunks = [data[:1], data[1:3], data[3:5], data[5:]]
    floats = list(iter_pcm16_stream(chunks))
    combined = np.concatenate(floats)
    expected = pcm16_bytes_to_float32(data)
    assert np.allclose(combined, expected)


def test_iter_pcm16_stream_discards_leftover_byte():
    # single byte cannot form a sample
    assert list(iter_pcm16_stream([b"\x01"])) == []
