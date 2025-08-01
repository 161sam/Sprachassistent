#!/usr/bin/env bash
set -e

### Option A: Installiere n8n & Flowise via Docker (Standard)
echo "Installing Docker & Docker Compose..."
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
sudo apt install -y docker-compose

mkdir -p flowise-data n8n-data

cat <<EOF > docker-compose.yml
version: '3.8'
services:
  flowise:
    image: elestio/flowiseai
    restart: always
    network_mode: host
    volumes:
      - \$(pwd)/flowise-data:/root/.flowise

  n8n:
    image: n8nio/n8n
    restart: always
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_HOST=localhost
      - N8N_PORT=5678
    volumes:
      - \$(pwd)/n8n-data:/home/node/.n8n
EOF

echo "Starting Docker services..."
docker-compose up -d

### Option B: Lokale NPM-Installation (nicht für Produktion)
read -p "Install n8n and Flowise globally via npm instead of Docker? [y/N]: " npmchoice

if [[ "$npmchoice" == "y" || "$npmchoice" == "Y" ]]; then
  echo "Installing NodeJS + npm packages for n8n & flowise..."
  sudo apt update
  sudo apt install -y nodejs npm
  npm install -g n8n flowise

  echo "Starting flowise in background..."
  nohup npx flowise start > flowise.log 2>&1 &
  echo "Flowise gestartet auf http://localhost:3000"

  echo "Zum Starten von n8n:"
  echo "  n8n"
  echo "  oder mit Tunnel: n8n start --tunnel"
fi

echo "✅ Setup abgeschlossen."
echo "🌐 Flowise: http://localhost:3000"
echo "🔁 n8n:     http://localhost:5678"
