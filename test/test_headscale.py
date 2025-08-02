import os
import requests
from dotenv import load_dotenv

load_dotenv()

api = os.getenv("HEADSCALE_API") or os.getenv("HEADSCALE_URL")
if not api:
    raise SystemExit("HEADSCALE_API not configured")

token = os.getenv("HEADSCALE_TOKEN") or os.getenv("HEADSCALE_API_KEY")
headers = {"Authorization": f"Bearer {token}"} if token else {}

url = f"{api.rstrip('/')}/api/v1/nodes"
try:
    resp = requests.get(url, headers=headers, timeout=5)
    resp.raise_for_status()
    data = resp.json()
    print("Headscale nodes:", len(data.get("nodes", [])))
except Exception as exc:
    raise SystemExit(f"Headscale request failed: {exc}")
