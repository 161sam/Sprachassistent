#!/usr/bin/env bash
set -e
echo "🔌 Installiere Tailscale..."
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --authkey "$TAILSCALE_AUTHKEY" --hostname sprachassistent
echo "✅ Tailscale verbunden"


