import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv("FLOWISE_URL")
flowise_id = os.getenv("FLOWISE_ID") or os.getenv("FLOWISE_FLOW_ID")
if not base_url or not flowise_id:
    raise SystemExit("FLOWISE_URL or FLOWISE_ID not configured")

url = f"{base_url.rstrip('/')}/api/v1/prediction/{flowise_id}"
headers = {"Content-Type": "application/json"}
if os.getenv("FLOWISE_TOKEN") or os.getenv("FLOWISE_API_KEY"):
    headers["Authorization"] = f"Bearer {os.getenv('FLOWISE_TOKEN') or os.getenv('FLOWISE_API_KEY')}"

try:
    resp = requests.post(url, headers=headers, json={"question": "ping"}, timeout=5)
    resp.raise_for_status()
    data = resp.json()
    print("Flowise answer:", data.get("text") or data.get("answer"))
except Exception as exc:
    raise SystemExit(f"Flowise request failed: {exc}")
