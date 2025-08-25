# ws_server/transport/fastapi_adapter.py
from __future__ import annotations

import asyncio
import base64
import io
import json
import os
from typing import Dict, Optional, Tuple

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# -----------------------------------------------------------------------------
# FastAPI setup
# -----------------------------------------------------------------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/handshake")
def handshake():
    return {
        "ok": True,
        "server": "ws_server",
        "version": "dev",
        "features": {"staged_tts": True, "stt": True, "tts": True},
    }


# -----------------------------------------------------------------------------
# Helpers (audio utils, STT buffer)
# -----------------------------------------------------------------------------
class STTSession:
    """Buffer für einen Audio‑Stream (int16 mono @ 16kHz)."""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._buf = bytearray()

    def add_chunk_b64_int16(self, b64: str) -> None:
        raw = base64.b64decode(b64)
        self._buf.extend(raw)

    def to_float32(self) -> Tuple[Optional[np.ndarray], int]:
        if not self._buf:
            return None, 0
        arr_i16 = np.frombuffer(self._buf, dtype=np.int16)
        arr_f32 = (arr_i16.astype(np.float32) / 32768.0).copy()
        return arr_f32, self.sample_rate


def _parse_data_url_to_bytes(data_url: str) -> bytes:
    """
    Erwartet z.B. "data:audio/wav;base64,<...>" oder "data:audio/webm;<...>".
    """
    if not data_url.startswith("data:"):
        raise ValueError("not a data URL")
    head, b64 = data_url.split(",", 1)
    if ";base64" not in head:
        from urllib.parse import unquote_to_bytes

        return unquote_to_bytes(b64)
    return base64.b64decode(b64)


def _decode_any_audio_to_float32_mono_16k(raw_bytes: bytes) -> Tuple[np.ndarray, int]:
    """
    Decode audio bytes (webm/ogg/wav) -> np.float32 mono @16k using PyAV.
    """
    try:
        import av  # type: ignore
        from av.audio.resampler import AudioResampler  # type: ignore
    except Exception as e:
        raise RuntimeError(f"PyAV not installed/usable: {e}")

    with av.open(io.BytesIO(raw_bytes)) as container:
        stream = next((s for s in container.streams if s.type == "audio"), None)
        if stream is None:
            raise RuntimeError("no audio stream")
        resampler = AudioResampler(format="s16", layout="mono", rate=16000)
        frames = []
        for packet in container.demux(stream):
            for frame in packet.decode():
                frame = resampler.resample(frame)
                frames.append(frame)
        if not frames:
            raise RuntimeError("no frames decoded")
        pcm = b"".join(f.planes[0].to_bytes() for f in frames)
        arr_i16 = np.frombuffer(pcm, dtype=np.int16)
        arr_f32 = (arr_i16.astype(np.float32) / 32768.0).copy()
        return arr_f32, 16000


# -----------------------------------------------------------------------------
# STT (faster-whisper)
# -----------------------------------------------------------------------------
async def run_faster_whisper(
    arr_f32: Optional[np.ndarray], sr: int, language: str = "de"
) -> str:
    """
    Transcribe using faster-whisper. Gibt "" zurück, wenn nichts decodierbar ist.
    """
    if arr_f32 is None or sr <= 0:
        return ""

    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception:
        # Kein fataler Fehler – wir antworten leer.
        return ""

    model_path = os.getenv("FASTER_WHISPER_MODEL", "base")
    # int8 ist ein guter CPU‑Default
    model = WhisperModel(model_path, compute_type="int8")
    segments, _info = model.transcribe(arr_f32, language=language, vad_filter=True)
    text = "".join([seg.text for seg in segments]) if segments else ""
    return (text or "").strip()


# -----------------------------------------------------------------------------
# Optional TTS
# -----------------------------------------------------------------------------
ENABLE_TTS = os.getenv("ENABLE_TTS", "0") == "1"
_tts_mgr = None


async def _ensure_tts_manager():
    global _tts_mgr
    if _tts_mgr is not None:
        return _tts_mgr
    if not ENABLE_TTS:
        return None
    from ws_server.tts.manager import TTSManager

    _tts_mgr = TTSManager()
    ok = await _tts_mgr.initialize()
    if not ok:
        _tts_mgr = None
    return _tts_mgr


async def _speak_to_wav_b64(text: str) -> Optional[str]:
    """
    Synthese text -> PCM WAV bytes -> base64. Rückgabe None, falls TTS inaktiv.
    """
    mgr = await _ensure_tts_manager()
    if not mgr:
        return None
    wav = await mgr.synthesize_text(text=text)
    if not wav:
        return None
    return base64.b64encode(wav).decode("ascii")


# -----------------------------------------------------------------------------
# GUI Control Handlers (LLM/TTS Settings, Tests)
# -----------------------------------------------------------------------------
async def _handle_gui_control(ws: WebSocket, payload: dict) -> bool:
    """
    Sehr einfache Handler für GUI-Events:
      - tts_test: erzeugt WAV und sendet {"type":"tts","format":"wav_base64","audio":...}
      - get_llm_models: liefert Dummy-Liste
      - switch_llm_model / set_llm_options: quittiert
      - switch_tts_engine / set_tts_voice / set_tts_options: quittiert
      - staged_tts_control / set_stt_options / clear_cache: quittieren
    """
    typ = payload.get("type")

    # --- TTS Test
    if typ == "tts_test":
        text = payload.get("content") or payload.get("text") or "Test 1 2 3."
        try:
            b64wav = await _speak_to_wav_b64(text)
            if b64wav:
                await ws.send_text(
                    json.dumps({"type": "tts", "format": "wav_base64", "audio": b64wav})
                )
                await ws.send_text(json.dumps({"type": "response", "content": text}))
            else:
                await ws.send_text(
                    json.dumps(
                        {"type": "error", "message": "TTS nicht aktiv (ENABLE_TTS=1?)"}
                    )
                )
        except Exception as e:
            await ws.send_text(
                json.dumps({"type": "error", "message": f"tts_test failed: {e}"})
            )
        return True

    # --- LLM Dummies
    if typ == "get_llm_models":
        await ws.send_text(
            json.dumps(
                {
                    "type": "llm_models",
                    "models": ["tiny-gguf", "base-gguf", "none"],
                    "current": "base-gguf",
                }
            )
        )
        return True

    if typ in ("switch_llm_model", "set_llm_options"):
        await ws.send_text(
            json.dumps(
                {
                    "type": "llm_model_switched",
                    "model": payload.get("model") or "base-gguf",
                }
            )
        )
        return True

    # --- TTS/STT Settings + staged tts (nur Acks for now)
    if typ in (
        "switch_tts_engine",
        "set_tts_voice",
        "set_tts_options",
        "staged_tts_control",
        "set_stt_options",
        "clear_cache",
    ):
        await ws.send_text(json.dumps({"type": "ok", "action": typ}))
        return True

    return False


# -----------------------------------------------------------------------------
# WebSocket
# -----------------------------------------------------------------------------
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    stream_sessions: Dict[str, STTSession] = {}

    try:
        while True:
            msg = await ws.receive()

            # (Optional) Binary Pfad (für später)
            if "bytes" in msg and msg["bytes"] is not None:
                # aktuell ignorieren
                continue

            data = msg.get("text")
            if not data:
                continue

            try:
                payload = json.loads(data)
            except Exception:
                # Ungültiges JSON ignorieren
                continue

            # Handshake
            if payload.get("op") == "hello":
                resp = {
                    "op": "ready",
                    "capabilities": {
                        "binaryAudio": False,
                        "staged_tts": True,
                        "stt": True,
                        "tts": ENABLE_TTS,
                    },
                    "stream_id": payload.get("stream_id"),
                }
                await ws.send_text(json.dumps(resp))
                continue

            typ = payload.get("type")

            # Zuerst GUI-Control Events abfangen
            handled = await _handle_gui_control(ws, payload)
            if handled:
                continue

            # Ping/Pong
            if typ == "ping":
                ts = payload.get("timestamp") or payload.get("client_timestamp")
                await ws.send_text(json.dumps({"type": "pong", "client_timestamp": ts}))
                continue

            # --- Streaming STT (int16 base64 chunks) ---
            if typ == "start_audio_stream":
                sid = payload.get("stream_id") or "s"
                sr = payload.get("config", {}).get("sampleRate", 16000)
                stream_sessions[sid] = STTSession(sample_rate=sr)
                await ws.send_text(
                    json.dumps({"type": "audio_stream_started", "stream_id": sid})
                )
                continue

            if typ == "audio_chunk":
                sid = payload.get("stream_id") or "s"
                sess = stream_sessions.setdefault(sid, STTSession())
                b64 = payload.get("chunk")
                if b64:
                    sess.add_chunk_b64_int16(b64)
                continue

            if typ == "end_audio_stream":
                sid = payload.get("stream_id") or "s"
                sess = stream_sessions.pop(sid, None)
                if not sess:
                    await ws.send_text(
                        json.dumps({"type": "audio_stream_ended", "stream_id": sid})
                    )
                    continue
                arr_f32, sr = sess.to_float32()
                text = await run_faster_whisper(arr_f32, sr)
                await ws.send_text(
                    json.dumps({"type": "response", "content": text or "(leer)"})
                )
                # optionaler TTS‑Rundlauf
                if ENABLE_TTS and text:
                    b64wav = await _speak_to_wav_b64(text)
                    if b64wav:
                        await ws.send_text(
                            json.dumps(
                                {"type": "tts", "format": "wav_base64", "audio": b64wav}
                            )
                        )
                await ws.send_text(
                    json.dumps({"type": "audio_stream_ended", "stream_id": sid})
                )
                continue

            # --- Single‑shot Data:URL Upload (Electron/Browser convenience) ---
            if typ == "audio":
                content = payload.get("content", "")
                try:
                    raw = _parse_data_url_to_bytes(content)
                    arr_f32, sr = _decode_any_audio_to_float32_mono_16k(raw)
                    text = await run_faster_whisper(arr_f32, sr)
                    await ws.send_text(
                        json.dumps({"type": "response", "content": text or "(leer)"})
                    )
                    if ENABLE_TTS and text:
                        b64wav = await _speak_to_wav_b64(text)
                        if b64wav:
                            await ws.send_text(
                                json.dumps(
                                    {
                                        "type": "tts",
                                        "format": "wav_base64",
                                        "audio": b64wav,
                                    }
                                )
                            )
                except Exception as e:
                    await ws.send_text(
                        json.dumps(
                            {"type": "error", "message": f"audio decode failed: {e}"}
                        )
                    )
                continue

            # --- Text‑Roundtrip (LLM stub/echo + optional TTS) ---
            if typ == "text":
                content = payload.get("content", "")
                # TODO: später LLM‑Antwort hier erzeugen
                await ws.send_text(json.dumps({"type": "response", "content": content}))
                if ENABLE_TTS and content:
                    b64wav = await _speak_to_wav_b64(content)
                    if b64wav:
                        await ws.send_text(
                            json.dumps(
                                {"type": "tts", "format": "wav_base64", "audio": b64wav}
                            )
                        )
                continue

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
