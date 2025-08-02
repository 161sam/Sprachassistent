# Faster-Whisper STT

## Setup
Run `scripts/install-faster-whisper.sh` to install the library and download the model configured via `.env`.

## Start
The STT engine is used by the WebSocket server or can be invoked via Python:
```
python3 -m faster_whisper.transcribe audio.wav
```

## Troubleshooting
- Ensure `ffmpeg` is installed for audio conversion.
- Use `WHISPER_DEVICE=cuda` on systems with CUDA.

## .env Example
```
WHISPER_MODEL_SIZE=medium-int8
WHISPER_DEVICE=cpu
WHISPER_LANG=de
```
