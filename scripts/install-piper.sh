#!/usr/bin/env bash

set -e
echo "📦 Installiere Piper TTS..."
sudo apt update && sudo apt install -y git python3-pip espeak-ng
pip3 install --upgrade piper-tts

MODEL_DIR="$HOME/.local/share/piper"
mkdir -p "$MODEL_DIR"
if [ ! -f "$MODEL_DIR/de-thorsten-low.onnx" ]; then
  echo "⬇️  Lade deutsches Sprachmodell herunter..."
  curl -L -o "$MODEL_DIR/de-thorsten-low.onnx" \
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de-thorsten-low.onnx"
fi
echo "✅ Piper TTS installiert"


