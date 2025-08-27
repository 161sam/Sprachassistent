from __future__ import annotations
import os, aiohttp, asyncio, logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class LMClient:
    def __init__(self, base: Optional[str]=None, api_key: Optional[str]=None, request_timeout: float=20.0):
        self.base = base or os.getenv("LLM_BASE_URL", "")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.timeout = aiohttp.ClientTimeout(total=request_timeout)

    async def list_models(self) -> Dict[str, Any]:
        if not self.base:
            return {"available": [], "data": [], "loaded": []}
        url = f"{self.base.rstrip('/')}/v1/models"
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        async with aiohttp.ClientSession(timeout=self.timeout) as s:
            async with s.get(url, headers=headers) as r:
                if r.status == 200:
                    data = await r.json()
                    return data if isinstance(data, dict) else {"data": data}
                return {"available": [], "data": [], "loaded": []}

    async def chat(self, model: str, messages: List[Dict[str, str]],
                   temperature: float=0.4, max_tokens: int=256,
                   tools: Optional[List[Dict[str, Any]]]=None,
                   tool_choice: Optional[str]=None) -> Dict[str, Any]:
        if not self.base:
            return {"choices":[{"message":{"content":""}}]}
        url = f"{self.base.rstrip('/')}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type":"application/json"} if self.api_key else {"Content-Type":"application/json"}
        payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        if tools: payload["tools"] = tools
        if tool_choice: payload["tool_choice"] = tool_choice
        async with aiohttp.ClientSession(timeout=self.timeout) as s:
            async with s.post(url, headers=headers, json=payload) as r:
                try:
                    return await r.json()
                except Exception:
                    txt = await r.text()
                    logger.warning("LLM non-JSON response: %s", txt[:500])
                    return {"choices":[{"message":{"content":""}}]}

def extract_content(resp: Dict[str, Any]) -> str:
    try:
        choices = resp.get("choices") or []
        if choices:
            msg = (choices[0] or {}).get("message") or {}
            return (msg.get("content") or "").strip()
    except Exception:
        pass
    return ""
