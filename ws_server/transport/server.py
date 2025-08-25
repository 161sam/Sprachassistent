from __future__ import annotations
import os, json, time, logging, asyncio
from typing import Dict, Optional

from ..metrics.collector import collector
from ..protocol.handshake import parse_client_hello, build_ready
from ..auth.token import verify_token
from ..routing.intent_router import IntentClassifier
from ..routing.skills import load_all_skills
from ..routing.external import call_flowise, call_n8n
from ..audio.vad import VoiceActivityDetector, VADConfig
from ..core.prompt import get_system_prompt
from ..core.llm import LMClient, extract_content
from ..stt import AsyncSTTEngine, pcm16_bytes_to_float32
from ..tts.manager import TTSManager
from .audio_streams import AudioStreamManager

logger = logging.getLogger(__name__)

class VoiceServer:
    def __init__(self) -> None:
        self.sample_rate = int(os.getenv("SAMPLE_RATE","16000"))
        self.chunk_ms = int(os.getenv("CHUNK_MS","20"))
        self.max_audio_duration = float(os.getenv("MAX_AUDIO_DURATION","10"))
        self.enable_engine_switching = os.getenv("ENABLE_TTS_SWITCHING","1") not in ("0","false","False")
        self.default_tts_voice = os.getenv("TTS_VOICE","de-thorsten-low")
        self.llm_enabled = os.getenv("LLM_ENABLED","0") in ("1","true","True")
        self.llm_temperature = float(os.getenv("LLM_TEMPERATURE","0.4"))
        self.llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS","256"))

        self.stt_engine = AsyncSTTEngine(
            model_size=os.getenv("STT_MODEL","tiny"),
            model_path=os.getenv("STT_MODEL_PATH") or None,
            device=os.getenv("STT_DEVICE","cpu"),
            workers=int(os.getenv("STT_WORKERS","1"))
        )
        self.tts_manager = TTSManager()
        self.classifier = IntentClassifier()
        self.skills = load_all_skills()
        self.llm = LMClient()
        self.llm_model: Optional[str] = None
        self.chat_histories: Dict[str, list] = {}
        self.stream_manager = AudioStreamManager(
            sample_rate=self.sample_rate,
            max_duration=self.max_audio_duration,
            on_text=self._ask_llm_proxy
        )

    async def initialize(self) -> None:
        await self.stt_engine.initialize()
        # Init TTS-Manager (einheitlich)
        await self.tts_manager.initialize()

        # LLM Discovery (optional)
        if self.llm_enabled:
            try:
                info = await self.llm.list_models()
                models = info.get("available") or info.get("data") or []
                self.llm_model = os.getenv("LLM_DEFAULT_MODEL","auto")
                if self.llm_model == "auto":
                    self.llm_model = models[0] if models else None
                if self.llm_model:
                    logger.info("LLM enabled. Using model: %s", self.llm_model)
                else:
                    logger.warning("LLM enabled but no models available; will fallback to skills.")
            except Exception as e:
                logger.warning("LLM discovery failed: %s", e)

    def _hist(self, client_id: str): return self.chat_histories.setdefault(client_id, [])
    def _hist_trim(self, client_id: str, max_turns: int=4):
        hist = self._hist(client_id)
        if len(hist) > 2*max_turns + 1:
            sys = hist[0] if hist and hist[0].get("role")=="system" else None
            tail = hist[-(2*max_turns):]
            self.chat_histories[client_id] = ([sys]+tail) if sys else tail

    async def _ask_llm_proxy(self, text: str) -> Optional[str]:
        # Platzhalter – ungenutzt in dieser Version; echte Orchestrierung im Text-Handler
        return None

    async def _ask_llm(self, client_id: str, user_text: str) -> Optional[str]:
        if not (self.llm_enabled and self.llm_model):
            return None
        msgs = self._hist(client_id)
        if not msgs or msgs[0].get("role")!="system":
            msgs.insert(0, {"role":"system","content": get_system_prompt()})
        msgs.append({"role":"user","content": user_text}); self._hist_trim(client_id)
        try:
            resp = await self.llm.chat(self.llm_model, msgs, temperature=self.llm_temperature, max_tokens=self.llm_max_tokens)
            content = extract_content(resp)
            content = " ".join(content.split())
            if content:
                msgs.append({"role":"assistant","content": content}); self._hist_trim(client_id)
                return content
        except Exception:
            logger.exception("LLM chat failed")
        return None

    async def handle_websocket(self, websocket, path: str="/ws") -> None:
        # --- Token/Handshake ---
        # (Logik analog Legacy-Server: Token aus Query/Subprotocol/Header)  :contentReference[oaicite:3]{index=3}
        client_ip = websocket.remote_address[0] if websocket.remote_address else ""
        raw_path = getattr(getattr(websocket, "request", None), "path", getattr(websocket, "path", path))

        # Token prüfen
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(raw_path or "/").query)
        token = q.get("token", [None])[0]
        if not token:
            auth = websocket.request_headers.get('Authorization') if hasattr(websocket, 'request_headers') else None
            if auth and auth.lower().startswith('bearer '): token = auth[7:].strip()
        if not token and getattr(websocket, 'subprotocol', None): token = websocket.subprotocol
        if not verify_token(token):
            await websocket.close(code=4401, reason="unauthorized"); return

        # Hello + READY  (Handshake wie im Legacy-Loop)  :contentReference[oaicite:4]{index=4}
        raw = await asyncio.wait_for(websocket.recv(), timeout=10)
        try:
            hello = json.loads(raw); parse_client_hello(hello)
        except Exception:
            await websocket.close(code=4400, reason="bad handshake"); return
        await websocket.send(json.dumps(build_ready({"binary_audio": True})))

        # TTS/Config Info für Client (übernommen)  :contentReference[oaicite:5]{index=5}
        avail = await self.tts_manager.get_available_engines()
        current = self.tts_manager.get_current_engine()
        await websocket.send(json.dumps({
            "type":"connected",
            "server_time": time.time(),
            "config": {"chunk_size": int(self.sample_rate*self.chunk_ms/1000), "sample_rate": self.sample_rate,
                       "max_duration": self.max_audio_duration, "tts_switching_enabled": self.enable_engine_switching},
            "tts_info": {"available_engines": avail, "current_engine": (current.value if current else None),
                         "switching_enabled": self.enable_engine_switching}
        }))

        # Message Loop (vereinheitlicht)  :contentReference[oaicite:6]{index=6}
        async for message in websocket:
            try:
                data = json.loads(message); collector.messages_total.labels(protocol="json").inc()
                typ = data.get("type")
                if typ == "start_audio_stream":
                    sid = await self.stream_manager.start_stream(client_ip or "client")
                    await websocket.send(json.dumps({"type":"stream_started","stream_id":sid}))
                elif typ == "audio_chunk":
                    b64 = data.get("data","")
                    import base64
                    await self.stream_manager.push_chunk(data.get("stream_id",""), base64.b64decode(b64))
                elif typ == "end_audio_stream":
                    pcm = await self.stream_manager.end_stream(data.get("stream_id",""))
                    # STT -> Routing/LLM -> TTS
                    text = await self.stt_engine.transcribe_audio(pcm or b"", sample_rate=self.sample_rate)
                    reply = await self._ask_llm(client_ip or "client", text) or text or ""
                    if reply:
                        wav = await self.tts_manager.synthesize_text(reply, voice=self.default_tts_voice)
                        await websocket.send(json.dumps({"type":"tts_result","text": reply}))
                        # (Audio-Streaming der WAV-Chunks existiert bereits clientseitig)
                elif typ == "text":
                    user = (data.get("text") or "").strip()
                    reply = await self._ask_llm(client_ip or "client", user) or user
                    wav = await self.tts_manager.synthesize_text(reply, voice=self.default_tts_voice)
                    await websocket.send(json.dumps({"type":"tts_result","text": reply}))
                elif typ == "get_llm_models":
                    info = await self.llm.list_models()
                    await websocket.send(json.dumps({"type":"llm_models","data": info}))
                elif typ == "switch_llm_model":
                    m = (data.get("model") or "").strip()
                    self.llm_model = m or self.llm_model; await websocket.send(json.dumps({"type":"llm_switched","model": self.llm_model}))
                elif typ == "ping":
                    await websocket.send(json.dumps({"type":"pong","t": time.time()}))
                else:
                    await websocket.send(json.dumps({"type":"error","message": f"Unknown message type: {typ}"}))
            except json.JSONDecodeError:
                await websocket.send(json.dumps({"type":"error","message":"Invalid JSON format"}))
            except Exception:
                logger.exception("Unhandled WS error")
                await websocket.send(json.dumps({"type":"error","message":"internal server error"}))
                break
# --- canonical entrypoint for CLI ---
def main():
    import os
    from .fastapi_adapter import app
    import uvicorn
    host = os.getenv("WS_HOST", os.getenv("BACKEND_HOST", "127.0.0.1"))
    port = int(os.getenv("WS_PORT", os.getenv("BACKEND_PORT", "48232")))
    return uvicorn.run(app, host=host, port=port)
