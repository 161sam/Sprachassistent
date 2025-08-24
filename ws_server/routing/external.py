from __future__ import annotations
import os, aiohttp, asyncio, logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

FLOWISE_URL = os.getenv("FLOWISE_URL", "")
FLOWISE_TOKEN = os.getenv("FLOWISE_TOKEN","")
N8N_URL = os.getenv("N8N_URL","")
N8N_TOKEN = os.getenv("N8N_TOKEN","")
RETRY_LIMIT = int(os.getenv("HTTP_RETRY_LIMIT","3") or "3")
RETRY_BACKOFF = float(os.getenv("HTTP_RETRY_BACKOFF","0.5") or "0.5")

async def call_flowise(query: str, session_id: str) -> str:
    if not FLOWISE_URL: return "Flowise nicht konfiguriert"
    payload = {"question": query, "sessionId": session_id}
    headers = {"Content-Type": "application/json"}
    if FLOWISE_TOKEN: headers["Authorization"] = f"Bearer {FLOWISE_TOKEN}"
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                async with s.post(FLOWISE_URL, headers=headers, json=payload) as r:
                    if r.status == 200:
                        data = await r.json()
                        return data.get("text") or data.get("answer") or "(keine Antwort von Flowise)"
                    return f"[Flowise Fehler {r.status}]"
        except asyncio.TimeoutError:
            logger.error("Flowise request timed out")
        except Exception:
            logger.exception("Flowise request failed")
        if attempt < RETRY_LIMIT:
            await asyncio.sleep(RETRY_BACKOFF * (2 ** (attempt - 1)))
    return "Fehler: Flowise nicht erreichbar"

async def call_n8n(query: str, session_id: str) -> str:
    if not N8N_URL: return "(n8n nicht konfiguriert)"
    payload = {"query": query, "sessionId": session_id}
    headers = {"Content-Type": "application/json"}
    if N8N_TOKEN: headers["Authorization"] = f"Bearer {N8N_TOKEN}"
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                async with s.post(N8N_URL, headers=headers, json=payload) as r:
                    if r.status == 200:
                        data = await r.json()
                        return data.get("reply", "OK, erledigt")
                    return f"[n8n Fehler {r.status}]"
        except asyncio.TimeoutError:
            logger.error("n8n request timed out")
        except Exception:
            logger.exception("n8n request failed")
        if attempt < RETRY_LIMIT:
            await asyncio.sleep(RETRY_BACKOFF * (2 ** (attempt - 1)))
    return "(n8n nicht erreichbar)"
