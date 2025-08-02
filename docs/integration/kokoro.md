# Kokoro TTS

## Setup
`scripts/install-kokoro.sh` installs dependencies and downloads the model specified in `.env.kokoro`.

## Start
Use the Kokoro engine via the WebSocket server after installation.

## Troubleshooting
- Check Python version (>=3.8).
- Verify model and voices files in `$KOKORO_MODEL_DIR`.

## .env Example
```
KOKORO_MODEL=kokoro-v1.0.int8.onnx
KOKORO_LANG=en-us
```
