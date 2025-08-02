#!/usr/bin/env bash

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/../.env" ] && source "$SCRIPT_DIR/../.env"

MODEL_DIR="${PIPER_MODEL_DIR:-$HOME/.local/share/piper}"
MODEL_FILE="${PIPER_MODEL:-de-thorsten-low.onnx}"

echo "📦 Installiere Piper TTS..."

sudo apt update && sudo apt install -y git python3-pip espeak-ng curl
pip3 install --upgrade piper-tts >/dev/null

# Install binary if not present
if ! command -v piper >/dev/null; then
  echo "⬇️  Installiere Piper Binary..."
  ARCH=$(uname -m)
  case "$ARCH" in
    x86_64) BINARY="piper_linux_x86_64" ;;
    aarch64|arm64) BINARY="piper_linux_aarch64" ;;
    *) echo "❌ Unsupported architecture: $ARCH"; exit 1 ;;
  esac
  TMP_DIR=$(mktemp -d)
  curl -L "https://github.com/rhasspy/piper/releases/latest/download/${BINARY}.tar.gz" | tar -xz -C "$TMP_DIR"
  sudo mv "$TMP_DIR/piper" /usr/local/bin/
  rm -rf "$TMP_DIR"
fi

mkdir -p "$MODEL_DIR"
MODEL_PATH="$MODEL_DIR/$MODEL_FILE"
if [ ! -f "$MODEL_PATH" ]; then
  echo "⬇️  Lade Modell $MODEL_FILE herunter..."
  curl -L -o "$MODEL_PATH" "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/$MODEL_FILE"
fi

echo "✅ Piper TTS installiert"
