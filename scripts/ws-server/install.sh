#!/usr/bin/env bash
set -e
echo "Installing WebSocket server dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip
pip3 install websockets aiohttp faster-whisper piper-tts

echo "Creating directory..."
mkdir -p ~/ws-server
cp ws-server.py ~/ws-server/
# TODO: ws-server.service ebenfalls kopieren und installieren
echo "Done. Enable service with: sudo systemctl enable ws-server.service"
