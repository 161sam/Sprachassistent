# Design Note: Streaming STT Conversion

## Context
`ws_server/stt/in_memory.py` only exposes helpers that convert full PCM16 byte buffers to NumPy arrays. Streaming STT requires processing audio incrementally without buffering the entire payload.

## Decision
Add a generator `iter_pcm16_stream(chunks)` that accepts an iterable of byte chunks. It will:
- keep leftover bytes that do not form a full sample between iterations,
- convert completed frames to float32 arrays in the range [-1.0, 1.0],
- yield each chunk's float32 array.

Existing helpers remain for backwards compatibility.

## Consequences
Streaming pipelines can consume audio chunk-by-chunk. Memory usage stays bounded and the API remains compatible with previous code.
