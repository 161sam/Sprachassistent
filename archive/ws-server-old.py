import asyncio
import websockets
import base64
import tempfile
import os
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from aiohttp import ClientSession, web
import aiofiles
import redis.asyncio as redis
from faster_whisper import WhisperModel
import ssl
import hashlib
import jwt
from contextlib import asynccontextmanager

# === CONFIGURATION ===
@dataclass
class ServerConfig:
    port: int = int(os.getenv("WS_PORT", 8123))
    http_port: int = int(os.getenv("HTTP_PORT", 8124))
    max_connections: int = int(os.getenv("MAX_CONNECTIONS", 100))
    auth_secret: str = os.getenv("JWT_SECRET", "your-jwt-secret-key")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # TLS Configuration
    use_tls: bool = os.getenv("WS_USE_TLS", "false").lower() == "true"
    cert_path: str = os.getenv("WS_CERT", "cert.pem")
    key_path: str = os.getenv("WS_KEY", "key.pem")
    
    # External Services
    flowise_host: str = os.getenv("FLOWISE_HOST", "http://odroid.headscale.lan:3000")
    flow_id: str = os.getenv("FLOWISE_FLOW_ID", "dein-flowise-flow-id")
    flowise_api_key: str = os.getenv("FLOWISE_API_KEY", "")
    n8n_url: str = os.getenv("N8N_URL", "http://odroid.headscale.lan:5678/webhook/intent")
    
    # Audio Configuration
    audio_chunk_size: int = int(os.getenv("AUDIO_CHUNK_SIZE", 4096))
    max_audio_duration: int = int(os.getenv("MAX_AUDIO_DURATION", 30))
    
    # STT/TTS Configuration
    stt_model: str = os.getenv("STT_MODEL", "base")
    stt_device: str = os.getenv("STT_DEVICE", "cpu")
    stt_precision: str = os.getenv("STT_PRECISION", "int8")
    tts_model: str = os.getenv("TTS_MODEL", "de-thorsten-low.onnx")

config = ServerConfig()

# === LOGGING SETUP ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/voice-assistant/ws-server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === CONNECTION MANAGER ===
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.connection_info: Dict[str, dict] = {}
        
    async def connect(self, websocket: websockets.WebSocketServerProtocol, client_id: str, user_info: dict):
        self.active_connections[client_id] = websocket
        self.connection_info[client_id] = {
            'user_info': user_info,
            'connected_at': datetime.now(),
            'last_activity': datetime.now(),
            'ip': websocket.remote_address[0] if websocket.remote_address else 'unknown'
        }
        logger.info(f"Client {client_id} connected from {websocket.remote_address}")
        
    async def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self.connection_info[client_id]
            logger.info(f"Client {client_id} disconnected")
            
    async def send_personal_message(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send(json.dumps(message))
                self.connection_info[client_id]['last_activity'] = datetime.now()
            except websockets.exceptions.ConnectionClosed:
                await self.disconnect(client_id)
                
    async def broadcast(self, message: dict, exclude_client: Optional[str] = None):
        if self.active_connections:
            tasks = []
            for client_id in list(self.active_connections.keys()):
                if client_id != exclude_client:
                    tasks.append(self.send_personal_message(client_id, message))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

# === AUDIO STREAMING HANDLER ===
class AudioStreamHandler:
    def __init__(self):
        self.active_streams: Dict[str, dict] = {}
        self.model = WhisperModel(config.stt_model, device=config.stt_device, compute_type=config.stt_precision)
        
    async def start_stream(self, client_id: str) -> str:
        stream_id = str(uuid.uuid4())
        self.active_streams[stream_id] = {
            'client_id': client_id,
            'audio_chunks': [],
            'start_time': time.time(),
            'total_size': 0
        }
        return stream_id
        
    async def add_audio_chunk(self, stream_id: str, chunk_data: bytes) -> bool:
        if stream_id not in self.active_streams:
            return False
            
        stream = self.active_streams[stream_id]
        
        # Check duration and size limits
        if (time.time() - stream['start_time'] > config.max_audio_duration or 
            stream['total_size'] > 10 * 1024 * 1024):  # 10MB limit
            return False
            
        stream['audio_chunks'].append(chunk_data)
        stream['total_size'] += len(chunk_data)
        return True
        
    async def finalize_stream(self, stream_id: str) -> Optional[str]:
        if stream_id not in self.active_streams:
            return None
            
        stream = self.active_streams.pop(stream_id)
        
        try:
            # Combine audio chunks
            audio_data = b''.join(stream['audio_chunks'])
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name
                
            # Transcribe with faster-whisper
            segments, info = self.model.transcribe(tmp_path)
            text = "".join(segment.text for segment in segments).strip()
            
            # Cleanup
            os.remove(tmp_path)
            
            logger.info(f"Transcribed audio: {text[:100]}...")
            return text or "(kein Text erkannt)"
            
        except Exception as e:
            logger.error(f"STT Error: {e}")
            return f"[STT Fehler: {e}]"

# === CACHING LAYER ===
class CacheManager:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        
    async def initialize(self):
        try:
            self.redis_client = redis.from_url(config.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory cache: {e}")
            self.redis_client = None
            
    async def get(self, key: str) -> Optional[str]:
        try:
            if self.redis_client:
                return await self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None
        
    async def set(self, key: str, value: str, expire: int = 3600):
        try:
            if self.redis_client:
                await self.redis_client.setex(key, expire, value)
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            
    async def generate_cache_key(self, text: str) -> str:
        return f"response:{hashlib.md5(text.lower().encode()).hexdigest()}"

# === TTS ENGINE ===
class TTSEngine:
    def __init__(self):
        self.model_path = os.path.expanduser(f"~/.local/share/piper/{config.tts_model}")
        
    async def synthesize(self, text: str, voice: str = "de-thorsten") -> Optional[str]:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as out_file:
                out_path = out_file.name
                
            # Run piper TTS asynchronously
            process = await asyncio.create_subprocess_exec(
                'piper',
                '--model', self.model_path,
                '--output_file', out_path,
                '--text', text,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(out_path):
                async with aiofiles.open(out_path, 'rb') as f:
                    audio_data = await f.read()
                    audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                    
                os.remove(out_path)
                return f"data:audio/wav;base64,{audio_b64}"
            else:
                logger.error(f"TTS Error: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"TTS Exception: {e}")
            return None

# === INTENT ROUTER ===
class IntentRouter:
    def __init__(self, cache_manager: CacheManager, tts_engine: TTSEngine):
        self.cache = cache_manager
        self.tts = tts_engine
        self.session: Optional[ClientSession] = None
        
    async def initialize(self):
        self.session = ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        
    async def route_intent(self, text: str) -> dict:
        # Check cache first
        cache_key = await self.cache.generate_cache_key(text)
        cached_response = await self.cache.get(cache_key)
        
        if cached_response:
            logger.info("Returning cached response")
            return json.loads(cached_response)
            
        # Route based on intent
        t = text.lower().strip()
        
        if any(word in t for word in ["zeit", "uhrzeit", "wie spät"]):
            response_text = datetime.now().strftime("Es ist %H:%M Uhr")
        elif any(word in t for word in ["licht", "musik", "volume", "timer"]):
            response_text = await self._route_to_local_skills(text)
        elif any(word in t for word in ["wetter", "garage", "status"]):
            response_text = await self._route_to_n8n(text)
        else:
            response_text = await self._route_to_flowise(text)
            
        # Generate TTS
        audio_data = await self.tts.synthesize(response_text)
        
        result = {
            "text": response_text,
            "audio": audio_data,
            "timestamp": datetime.now().isoformat(),
            "cached": False
        }
        
        # Cache response
        await self.cache.set(cache_key, json.dumps(result), 1800)  # 30 min cache
        
        return result
        
    async def _route_to_local_skills(self, text: str) -> str:
        # Implement local skills
        t = text.lower()
        if "licht" in t:
            if "an" in t:
                return "Licht wurde eingeschaltet"
            elif "aus" in t:
                return "Licht wurde ausgeschaltet"
        elif "musik" in t:
            if "start" in t or "spiel" in t:
                return "Musik wird gestartet"
            elif "stopp" in t:
                return "Musik wurde gestoppt"
        return "Lokale Aktion wurde ausgeführt"
        
    async def _route_to_flowise(self, text: str) -> str:
        url = f"{config.flowise_host}/api/v1/prediction/{config.flow_id}"
        headers = {"Content-Type": "application/json"}
        if config.flowise_api_key:
            headers["Authorization"] = f"Bearer {config.flowise_api_key}"
            
        try:
            async with self.session.post(url, headers=headers, json={"question": text}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("text", "(keine Antwort von Flowise)")
                else:
                    return f"[Flowise Fehler {resp.status}]"
        except Exception as e:
            logger.error(f"Flowise error: {e}")
            return f"[Flowise nicht erreichbar: {e}]"
            
    async def _route_to_n8n(self, text: str) -> str:
        try:
            async with self.session.post(config.n8n_url, json={"query": text}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("reply", "(keine Antwort von n8n)")
                else:
                    return f"[n8n Fehler {resp.status}]"
        except Exception as e:
            logger.error(f"n8n error: {e}")
            return f"[n8n nicht erreichbar: {e}]"

# === AUTHENTICATION ===
class AuthManager:
    def __init__(self):
        self.secret = config.auth_secret
        
    def generate_token(self, user_data: dict) -> str:
        payload = {
            'user': user_data,
            'exp': datetime.utcnow().timestamp() + 3600,  # 1 hour
            'iat': datetime.utcnow().timestamp()
        }
        return jwt.encode(payload, self.secret, algorithm='HS256')
        
    def verify_token(self, token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, self.secret, algorithms=['HS256'])
            return payload.get('user')
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None

# === MAIN APPLICATION ===
class VoiceAssistantServer:
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.audio_handler = AudioStreamHandler()
        self.cache_manager = CacheManager()
        self.tts_engine = TTSEngine()
        self.intent_router = IntentRouter(self.cache_manager, self.tts_engine)
        self.auth_manager = AuthManager()
        
    async def initialize(self):
        await self.cache_manager.initialize()
        await self.intent_router.initialize()
        logger.info("Voice Assistant Server initialized")
        
    async def handle_websocket(self, websocket, path):
        client_id = str(uuid.uuid4())
        
        try:
            # Authentication
            auth_msg = await asyncio.wait_for(websocket.recv(), timeout=10)
            auth_data = json.loads(auth_msg)
            
            user_info = self.auth_manager.verify_token(auth_data.get("token", ""))
            if not user_info:
                await websocket.send(json.dumps({"error": "Authentication failed"}))
                return
                
            # Register connection
            await self.connection_manager.connect(websocket, client_id, user_info)
            
            # Send welcome message
            await self.connection_manager.send_personal_message(client_id, {
                "type": "connected",
                "client_id": client_id,
                "message": "Erfolgreich verbunden"
            })
            
            # Message handling loop
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(client_id, data)
                except json.JSONDecodeError:
                    await self.connection_manager.send_personal_message(client_id, {
                        "type": "error",
                        "message": "Invalid JSON format"
                    })
                    
        except Exception as e:
            logger.error(f"WebSocket error for {client_id}: {e}")
        finally:
            await self.connection_manager.disconnect(client_id)
            
    async def _handle_message(self, client_id: str, data: dict):
        message_type = data.get("type")
        
        if message_type == "text":
            await self._handle_text_message(client_id, data)
        elif message_type == "audio_start":
            await self._handle_audio_start(client_id, data)
        elif message_type == "audio_chunk":
            await self._handle_audio_chunk(client_id, data)
        elif message_type == "audio_end":
            await self._handle_audio_end(client_id, data)
        elif message_type == "ping":
            await self.connection_manager.send_personal_message(client_id, {
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            })
        else:
            await self.connection_manager.send_personal_message(client_id, {
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            })
            
    async def _handle_text_message(self, client_id: str, data: dict):
        user_input = data.get("content", "").strip()
        if not user_input:
            return
            
        logger.info(f"[{client_id}] Text input: {user_input}")
        
        # Process with intent router
        response = await self.intent_router.route_intent(user_input)
        
        await self.connection_manager.send_personal_message(client_id, {
            "type": "response",
            "content": response["text"],
            "audio": response["audio"],
            "timestamp": response["timestamp"]
        })
        
    async def _handle_audio_start(self, client_id: str, data: dict):
        stream_id = await self.audio_handler.start_stream(client_id)
        await self.connection_manager.send_personal_message(client_id, {
            "type": "audio_ready",
            "stream_id": stream_id
        })
        
    async def _handle_audio_chunk(self, client_id: str, data: dict):
        stream_id = data.get("stream_id")
        chunk_b64 = data.get("chunk")
        
        if not stream_id or not chunk_b64:
            return
            
        try:
            chunk_data = base64.b64decode(chunk_b64)
            success = await self.audio_handler.add_audio_chunk(stream_id, chunk_data)
            
            if not success:
                await self.connection_manager.send_personal_message(client_id, {
                    "type": "audio_error",
                    "message": "Audio stream limit exceeded"
                })
        except Exception as e:
            logger.error(f"Audio chunk error: {e}")
            
    async def _handle_audio_end(self, client_id: str, data: dict):
        stream_id = data.get("stream_id")
        if not stream_id:
            return
            
        # Transcribe audio
        transcription = await self.audio_handler.finalize_stream(stream_id)
        
        if transcription:
            logger.info(f"[{client_id}] Audio transcribed: {transcription}")
            
            # Process with intent router
            response = await self.intent_router.route_intent(transcription)
            
            await self.connection_manager.send_personal_message(client_id, {
                "type": "response",
                "content": response["text"],
                "audio": response["audio"],
                "timestamp": response["timestamp"],
                "transcription": transcription
            })
        else:
            await self.connection_manager.send_personal_message(client_id, {
                "type": "error",
                "message": "Audio transcription failed"
            })

# === HTTP API (for health checks, metrics, etc.) ===
async def health_check(request):
    return web.json_response({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "connections": len(app.connection_manager.active_connections)
    })

async def metrics(request):
    return web.json_response({
        "active_connections": len(app.connection_manager.active_connections),
        "connection_info": {
            client_id: {
                "connected_at": info["connected_at"].isoformat(),
                "last_activity": info["last_activity"].isoformat(),
                "ip": info["ip"]
            }
            for client_id, info in app.connection_manager.connection_info.items()
        }
    })

# === SERVER STARTUP ===
async def main():
    global app
    app = VoiceAssistantServer()
    await app.initialize()
    
    # Setup HTTP server for API
    http_app = web.Application()
    http_app.router.add_get('/health', health_check)
    http_app.router.add_get('/metrics', metrics)
    
    # Start HTTP server
    http_runner = web.AppRunner(http_app)
    await http_runner.setup()
    http_site = web.TCPSite(http_runner, '0.0.0.0', config.http_port)
    
    logger.info(f"Starting HTTP API server on port {config.http_port}")
    await http_site.start()
    
    # Setup WebSocket server
    kwargs = {
        "max_size": 10_000_000,
        "ping_interval": 20,
        "ping_timeout": 10,
        "close_timeout": 10
    }
    
    if config.use_tls:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile=config.cert_path, keyfile=config.key_path)
        kwargs["ssl"] = ssl_context
        
    logger.info(f"🚀 Starting WebSocket server on port {config.port}")
    
    # Store app reference for HTTP handlers
    app.connection_manager = app.connection_manager
    
    async with websockets.serve(app.handle_websocket, "0.0.0.0", config.port, **kwargs):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
