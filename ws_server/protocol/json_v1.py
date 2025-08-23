"""JSON based message helpers (protocol v1)."""

import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

def parse_message(data: str) -> Dict[str, Any]:
    return json.loads(data)

class JsonMessageHandler:
    def __init__(self, tts_manager, staged_processor, intent_router=None):
        self.tts_manager = tts_manager
        self.staged = staged_processor
        self.intent_router = intent_router

    async def handle_message(self, ws, data: dict):
        mtype = data.get("type")
        if not mtype:
            return

        # ---- keepalive ----
        if mtype == "ping":
            ts = data.get("timestamp") or data.get("client_timestamp")
            await ws.send(json.dumps({"type": "pong", "client_timestamp": ts}))
            return

        # ---- audio start ack ----
        if mtype == "start_audio_stream":
            stream_id = data.get("stream_id") or "default"
            await ws.send(json.dumps({"type": "audio_stream_started", "stream_id": stream_id}))
            return

        # ---- info ----
        if mtype == "get_tts_info":
            info = self.tts_manager.get_info()
            await ws.send(json.dumps({"type": "tts_info", **info}))
            return

        if mtype == "staged_tts_control":
            action = (data.get("action") or "").lower()
            if action == "get_stats":
                stats = self.staged.get_cache_stats()
                await ws.send(json.dumps({"type": "staged_tts_stats", **stats}))
                return
            if action == "clear_cache":
                self.staged.clear_cache()
                await ws.send(json.dumps({"type": "staged_tts_cache", "message": "Cache geleert"}))
                return
            return

        if mtype == "text":
            raw_text = data.get("content") or data.get("text") or ""
            if not raw_text:
                return
            canonical_voice = self.tts_manager.get_canonical_voice(
                data.get("tts_voice") or None
            )
            chunks = await self.staged.process_staged_tts(raw_text, canonical_voice)
            for ch in chunks:
                await ws.send(json.dumps(self.staged.create_chunk_message(ch)))
            await ws.send(json.dumps(
                self.staged.create_sequence_end_message(
                    chunks[0].sequence_id if chunks else "00000000"
                )
            ))
            return

__all__ = ["parse_message", "JsonMessageHandler"]
