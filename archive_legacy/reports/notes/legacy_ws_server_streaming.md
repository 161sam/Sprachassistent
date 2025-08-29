# Legacy WS server streaming

- Log Kokoro voice detection errors instead of silently ignoring them.
- Stream PCM16 audio chunks via `process_binary_audio` without buffering.
- Return transcription dict per chunk to support incremental STT handling.
