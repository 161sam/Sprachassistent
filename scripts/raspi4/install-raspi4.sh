#!/usr/bin/env bash
set -e
echo "Installing Faster‑Whisper..."
sudo apt update && sudo apt install -y python3-pip git libsndfile1
pip3 install faster-whisper

echo "Installing Piper TTS..."
pip3 install piper-tts
sudo apt install -y espeak-ng

echo "Test TTS..."
echo "Hallo Welt" > /tmp/text.txt
piper --model de-thorsten-low.onnx --text-file /tmp/text.txt --output-file /tmp/test.wav || echo "TTS failed"

echo "Configuration files are in config/raspi4/"
