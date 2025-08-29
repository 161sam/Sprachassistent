import numpy as np

def test_to_int16_does_not_peak_normalize():
    from ws_server.tts.staged_tts.adapter import _to_int16
    x1 = np.array([0.2, -0.2], dtype=np.float32)
    x2 = np.array([0.8, -0.8], dtype=np.float32)
    i1 = _to_int16(x1)
    i2 = _to_int16(x2)
    # expect roughly 4x amplitude between 0.2 and 0.8, not normalized to same peak
    ratio = abs(int(i2[0])) / max(1, abs(int(i1[0])))
    assert 3.5 <= ratio <= 4.5
