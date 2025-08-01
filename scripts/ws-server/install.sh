#!/usr/bin/env bash
set -e
echo "Installing WebSocket server dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip
pip3 install websockets aiohttp faster-whisper piper-tts

echo "Creating directory..."
mkdir -p ~/ws-server
cp ws-server.py ~/ws-server/
sudo cp ws-server.service /etc/systemd/system/ws-server.service
sudo systemctl daemon-reload
echo "Done. Enable service with: sudo systemctl enable --now ws-server.service"
