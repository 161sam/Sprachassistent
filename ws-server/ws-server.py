import asyncio
import websockets
import base64
import tempfile
import os
import json
from datetime import datetime
from aiohttp import ClientSession
from faster_whisper import WhisperModel
import ssl

# === KONFIGURATION ===
PORT = 8123
AUTHORIZED_TOKENS = ["mein-geheimer-token"]
ALLOWED_IPS = ["127.0.0.1", "100.100.100.23"]  # Tailscale-IP-Adressen

USE_TLS = False
CERT_PATH = "cert.pem"
KEY_PATH = "key.pem"

FLOWISE_HOST = "http://odroid-n2.tailnet-name.ts.net:3000"
FLOW_ID = "dein-flowise-flow-id"
FLOWISE_API_KEY = ""

N8N_URL = "http://odroid-n2.tailnet-name.ts.net:5678/webhook/intent"

# === STT-MODELL LADEN ===
model = WhisperModel("base", device="cpu", compute_type="int8")

# === IP-CHECK ===
def is_allowed_ip(address):
    return address[0] in ALLOWED_IPS

# === STT ===
async def transcribe_audio(base64_audio: str) -> str:
    try:
        audio_bytes = base64.b64decode(base64_audio.split(",")[1])
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        segments, info = model.transcribe(tmp_path)
        text = "".join(segment.text for segment in segments)
        os.remove(tmp_path)
        return text.strip() or "(kein Text erkannt)"
    except Exception as e:
        return f"[STT Fehler: {e}]"

# === TTS ===
async def synthesize_tts(text: str) -> str:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as out_file:
            out_path = out_file.name
        os.system(f'piper --model ~/.local/share/piper/de-thorsten-low.onnx --output_file {out_path} --text \"{text}\"')
        with open(out_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")
        os.remove(out_path)
        return f"data:audio/wav;base64,{audio_b64}"
    except Exception as e:
        return ""

# === FLOWISE ===
async def route_to_flowise(text: str) -> str:
    url = f"{FLOWISE_HOST}/api/v1/prediction/{FLOW_ID}"
    headers = {"Content-Type": "application/json"}
    if FLOWISE_API_KEY:
        headers["Authorization"] = f"Bearer {FLOWISE_API_KEY}"
    try:
        async with ClientSession() as session:
            async with session.post(url, headers=headers, json={"question": text}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("text", "(keine Antwort von Flowise)")
                else:
                    return f"[Flowise Fehler {resp.status}]"
    except Exception as e:
        return f"[Flowise nicht erreichbar: {e}]"

# === N8N ===
async def route_to_n8n(text: str) -> str:
    try:
        async with ClientSession() as session:
            async with session.post(N8N_URL, json={"query": text}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("reply", "(keine Antwort von n8n)")
                else:
                    return f"[n8n Fehler {resp.status}]"
    except Exception as e:
        return f"[n8n nicht erreichbar: {e}]"

# === INTENT-ROUTING ===
async def route_intent(text: str) -> str:
    t = text.lower().strip()
    if any(word in t for word in ["licht", "musik", "volume", "timer"]):
        # TODO: Lokale Skill-Implementierung anbinden
        return "[lokale Skills noch nicht implementiert]"
    elif any(word in t for word in ["wetter", "garage", "status", "zeit"]):
        return await route_to_n8n(t)
    else:
        return await route_to_flowise(t)

# === WEBSOCKET HANDLER ===
async def handle_message(websocket, path):
    client_ip = websocket.remote_address[0]
    print(f"[{datetime.now()}] Verbindung von {client_ip}")

    if not is_allowed_ip(websocket.remote_address):
        await websocket.send("🚫 Zugriff verweigert: IP nicht erlaubt")
        await websocket.close()
        return

    try:
        auth_msg = await asyncio.wait_for(websocket.recv(), timeout=5)
        auth_data = json.loads(auth_msg)
        if auth_data.get("token") not in AUTHORIZED_TOKENS:
            await websocket.send("🚫 Ungültiger Token")
            await websocket.close()
            return
    except Exception as e:
        await websocket.send("🚫 Authentifizierung fehlgeschlagen")
        await websocket.close()
        return

    try:
        async for message in websocket:
            data = json.loads(message)

            if data["type"] == "text":
                user_input = data["content"]
                print(f"[TEXT] {user_input}")
                reply = await route_intent(user_input)
                audio = await synthesize_tts(reply)
                await websocket.send(json.dumps({
                    "type": "tts",
                    "text": reply,
                    "audio": audio
                }))

            elif data["type"] == "audio":
                print("[AUDIO] Sprachdaten empfangen…")
                result = await transcribe_audio(data["content"])
                reply = await route_intent(result)
                audio = await synthesize_tts(reply)
                await websocket.send(json.dumps({
                    "type": "tts",
                    "text": reply,
                    "audio": audio
                }))

            else:
                await websocket.send("❓ Unbekannter Nachrichtentyp")

    except websockets.exceptions.ConnectionClosed:
        print(f"[{datetime.now()}] Verbindung getrennt: {client_ip}")

# === SERVER START ===
async def main():
    print(f"🧠 Starte WebSocket-Server auf Port {PORT}...")
    kwargs = {
        "max_size": 10_000_000
    }
    if USE_TLS:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile=CERT_PATH, keyfile=KEY_PATH)
        kwargs["ssl"] = ssl_context

    async with websockets.serve(handle_message, "0.0.0.0", PORT, **kwargs):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
