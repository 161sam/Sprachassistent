# Piper TTS

## Setup
Run `scripts/install-piper.sh` to install Piper and download the model defined in `.env`.

## Start
`scripts/start-tts.sh "Hallo Welt"`

## Troubleshooting
- Ensure `PIPER_MODEL` exists in `PIPER_MODEL_DIR`.
- Install audio playback utilities like `aplay`.

## .env Example
```
PIPER_MODEL=de-thorsten-low.onnx
PIPER_MODEL_DIR=./models/piper
```
