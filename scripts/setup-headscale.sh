#!/usr/bin/env bash
set -e

# Install headscale server on ARM (e.g. Odroid)
HEADSCALE_VERSION="0.26.1"
HEADSCALE_ARCH="arm64"

echo "🔌 Installiere Headscale ${HEADSCALE_VERSION}..."
wget -O headscale.deb "https://github.com/juanfont/headscale/releases/download/v${HEADSCALE_VERSION}/headscale_${HEADSCALE_VERSION}_linux_${HEADSCALE_ARCH}.deb"

sudo apt install -y ./headscale.deb

sudo cp Headscale/headscale.systemd.service /etc/systemd/system/headscale.service
sudo systemctl daemon-reload
sudo systemctl enable --now headscale.service

echo "✅ Headscale installiert und gestartet"
