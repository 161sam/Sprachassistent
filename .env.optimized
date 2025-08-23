# Optimierte .env-Konfiguration für Staged TTS
# Löst Piper-Timeout und Phonem-Probleme

# === Server ===
PING_INTERVAL=20
PING_TIMEOUT=10
WS_HOST=127.0.0.1
WS_PORT=48231
METRICS_PORT=48232

# === STT (faster-whisper via CTranslate2) ===
STT_MODEL=openai/whisper-base
STT_DEVICE=cuda
STT_PRECISION=int8
SAMPLE_RATE=16000
AUDIO_CHUNK_SIZE=1024

# === TTS Basis-Konfiguration ===
TTS_MODEL_DIR=models
TTS_ENGINE=zonos
TTS_VOICE=de_DE-thorsten-low
TTS_SPEED=1.0
TTS_VOLUME=1.0

# === Zonos (Hauptengine) ===
ZONOS_MODEL=Zyphra/Zonos-v0.1-transformer
ZONOS_LANG=de
ZONOS_VOICE=thorsten
ZONOS_SPEAKER_DIR=spk_cache
TTS_OUTPUT_SR=48000

# === Piper (Intro-Engine) ===
PIPER_MODEL_DIR=/home/saschi/Sprachassistent/models/piper

# === Staged TTS - Optimierte Einstellungen ===
STAGED_TTS_ENABLED=true
STAGED_TTS_DEBUG=true

# Engine-Zuordnung
STAGED_TTS_INTRO_ENGINE=piper
STAGED_TTS_MAIN_ENGINE=zonos
STAGED_TTS_FALLBACK_ENGINE=zonos

# Text-Splitting (angepasst für bessere Performance)
STAGED_TTS_MAX_RESPONSE_LENGTH=600    # Reduziert von 800
STAGED_TTS_MAX_INTRO_LENGTH=120       # Reduziert von 150
STAGED_TTS_CHUNK_SIZE_MIN=80
STAGED_TTS_CHUNK_SIZE_MAX=180         # Reduziert von 200

# Timeout-Einstellungen (kritische Anpassungen)
STAGED_TTS_INTRO_TIMEOUT=6.0          # Reduziert von 10s auf 6s
STAGED_TTS_CHUNK_TIMEOUT=10.0         # Reduziert von 15s auf 10s  
STAGED_TTS_TOTAL_TIMEOUT=35.0         # Reduziert von 45s auf 35s

# Retry-Verhalten
STAGED_TTS_MAX_RETRIES=1              # Reduziert von 2 auf 1
STAGED_TTS_RETRY_DELAY=0.3            # Schnellerer Retry

# Caching
STAGED_TTS_ENABLE_CACHING=true
STAGED_TTS_CACHE_SIZE=100
STAGED_TTS_CACHE_TTL=3600

# Fallback-Strategien (wichtig!)
STAGED_TTS_FALLBACK_ON_TIMEOUT=true   # Bei Timeout zu Zonos wechseln
STAGED_TTS_FALLBACK_ON_ERROR=true     # Bei Fehler zu Zonos wechseln
STAGED_TTS_ALLOW_PARTIAL=true         # Teilweise Ausgabe erlauben

# Text-Bereinigung (kritisch für Phonem-Problem)
STAGED_TTS_SANITIZE_TEXT=true         # Text-Bereinigung aktivieren
STAGED_TTS_STRICT_ASCII=false         # Deutsche Umlaute beibehalten
STAGED_TTS_REMOVE_DIACRITICS=true     # Diakritika entfernen

# Performance-Monitoring
STAGED_TTS_LOG_PERFORMANCE=true
STAGED_TTS_PERFORMANCE_WARNINGS=true

# Kompatibilitäts-Einstellungen
TTS_ENGINES=piper,zonos
WS_TTS_PUSH_JSON=1
AUDIO_OUTPUT=staged
AUTOPLAY=1

# === Kokoro (optional, derzeit deaktiviert) ===
KOKORO_MODEL_PATH=/home/saschi/Sprachassistent/models/kokoro/kokoro-v1.0.onnx
KOKORO_VOICES_PATH=/home/saschi/Sprachassistent/models/kokoro/voices-v1.0.bin
KOKORO_DISABLE_DOWNLOAD=1

# === Skills/External ===
ENABLED_SKILLS=
SAVE_DEBUG_AUDIO=false
JWT_SECRET=devsecret
ALLOWED_ORIGINS=*
ALLOWED_IPS=
LOGLEVEL=INFO
JWT_ALLOW_PLAIN=1
JWT_BYPASS=0

# === Python Environment ===
BACKEND_PY=/home/saschi/Sprachassistent/.venv/bin/python3
PYTHON=/home/saschi/Sprachassistent/.venv/bin/python3
MODELS_DIR=/home/saschi/Sprachassistent/models

# === Phonem-Problem Fixes ===
# Spezielle Einstellungen für Piper TTS
PIPER_PHONEME_STRICT=false            # Weniger strenge Phonem-Validierung
PIPER_FALLBACK_ON_UNKNOWN=true        # Bei unbekannten Phonemen weitermachen
PIPER_NORMALIZE_TEXT=true             # Text vor Verarbeitung normalisieren

# Unicode-Handling
UNICODE_NORMALIZE=NFKC                # Unicode-Normalisierung
REMOVE_PROBLEMATIC_CHARS=true         # Problematische Zeichen entfernen

# === Erweiterte Debugging-Optionen ===
STAGED_TTS_TRACE_CHUNKS=false         # Detailliertes Chunk-Tracing
STAGED_TTS_SAVE_AUDIO=false           # Audio-Chunks für Debugging speichern
STAGED_TTS_BENCHMARK_MODE=false       # Benchmark-Modus für Tests

# === Hardware-Optimierung ===
TORCH_THREADS=4                       # CPU-Threads für PyTorch
OMP_NUM_THREADS=4                     # OpenMP Threads
CUDA_VISIBLE_DEVICES=0                # GPU-Auswahl