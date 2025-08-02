# n8n

## Setup
Install using `scripts/install-n8n.sh`. The script supports local npm installation or Docker based on `.env.n8n`.

## Start
Run `scripts/start-n8n.sh` to launch n8n.

## Troubleshooting
- Ensure Node.js and npm are installed for local mode.
- For Docker mode, verify the Docker daemon is running.

## .env Example
```
N8N_HOST=localhost
N8N_PORT=5678
N8N_API_KEY=changeme
N8N_DOCKER=false
```
