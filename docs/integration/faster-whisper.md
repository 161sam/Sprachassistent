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
- Use `STT_DEVICE=cuda` on systems with CUDA.

## .env Example
```
STT_MODEL=Systran/faster-whisper-base
STT_DEVICE=cpu
STT_PRECISION=int8
```

> ⚠️ Using repositories such as `openai/whisper-base` will download the
> original PyTorch weights which miss the required CTranslate2 files.  Set
> `STT_MODEL` to the corresponding `Systran/faster-whisper-*` repository to
> avoid startup warnings and ensure faster-whisper works correctly.
