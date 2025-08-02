#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/../.env.headscale" ] && source "$SCRIPT_DIR/../.env.headscale"

ARCH=$(uname -m)
case "$ARCH" in
  x86_64) HEADSCALE_ARCH="amd64" ;;
  aarch64|arm64) HEADSCALE_ARCH="arm64" ;;
  *) echo "❌ Unsupported architecture: $ARCH"; exit 1 ;;
esac

HEADSCALE_VERSION="${HEADSCALE_VERSION:-0.26.1}"

echo "🔌 Installiere Headscale ${HEADSCALE_VERSION} für ${HEADSCALE_ARCH}..."
wget -O headscale.deb "https://github.com/juanfont/headscale/releases/download/v${HEADSCALE_VERSION}/headscale_${HEADSCALE_VERSION}_linux_${HEADSCALE_ARCH}.deb"

sudo apt install -y ./headscale.deb

sudo cp headscale/headscale.systemd.service /etc/systemd/system/headscale.service
sudo systemctl daemon-reload
sudo systemctl enable --now headscale.service

echo "✅ Headscale installiert und gestartet"
