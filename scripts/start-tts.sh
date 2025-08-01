#!/usr/bin/env bash
text="${1:-Hallo Welt}"
model="${TTS_MODEL:-de-thorsten-low.onnx}"
echo "🔊 Spreche: $text"
piper --model "$model" --output_file /tmp/tts.wav --text "$text"
aplay /tmp/tts.wav

