#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/../.env" ] && source "$SCRIPT_DIR/../.env"
text="${1:-Hallo Welt}"
model="${PIPER_MODEL:-de-thorsten-low.onnx}"
echo "🔊 Spreche: $text"
piper --model "$model" --output_file /tmp/tts.wav --text "$text"
aplay /tmp/tts.wav
