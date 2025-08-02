#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/../.env" ] && source "$SCRIPT_DIR/../.env"

MODEL_SIZE="${WHISPER_MODEL_SIZE:-small}"
DEVICE="${WHISPER_DEVICE:-cpu}"
LANG="${WHISPER_LANG:-en}"

echo "🎧 Installiere Faster-Whisper (${MODEL_SIZE})..."

sudo apt update && sudo apt install -y python3-pip ffmpeg
pip3 install --upgrade faster-whisper >/dev/null

python3 - <<PY
from faster_whisper import WhisperModel
WhisperModel("${MODEL_SIZE}", device="${DEVICE}")
print("Model downloaded")
PY

echo "✅ Faster-Whisper installiert"
