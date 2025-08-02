import os
import sys
import json
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parent.parent))

load_dotenv()

url = os.getenv("N8N_URL") or os.getenv("N8N_WEBHOOK_URL")
if not url:
    raise SystemExit("N8N_URL not configured")

token = os.getenv("N8N_TOKEN") or os.getenv("N8N_API_KEY")
headers = {"Content-Type": "application/json"}
if token:
    headers["Authorization"] = f"Bearer {token}"

try:
    resp = requests.post(url, headers=headers, json={"query": "ping"}, timeout=5)
    resp.raise_for_status()
    print("n8n response:", resp.text[:200])
except Exception as exc:
    raise SystemExit(f"n8n request failed: {exc}")
