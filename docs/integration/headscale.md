# Headscale

## Setup
Use `scripts/setup-headscale.sh` to install Headscale. Configuration is read from `.env.headscale`.

## Start
The script installs and enables `headscale.service` automatically.

## Troubleshooting
- Verify the architecture is supported (`amd64` or `arm64`).
- Check logs with `journalctl -u headscale`.

## .env Example
```
HEADSCALE_VERSION=0.26.1
HEADSCALE_DOMAIN=example.com
HEADSCALE_KEY_DIR=/var/lib/headscale
```
