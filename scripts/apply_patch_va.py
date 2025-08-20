#!/usr/bin/env python3
import re, sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]

ws = root / "backend/ws-server/ws-server.py"
fastapi = root / "backend/ws-server/ws_server_fastapi.py"
ttsmgr = root / "backend/tts/tts_manager.py"
install_sh = root / "scripts/install_torch.sh"

def read(p): return p.read_text(encoding="utf-8")
def write(p, s):
    b = p.with_suffix(p.suffix + ".bak")
    if not b.exists():
        b.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    p.write_text(s, encoding="utf-8")

def patch_ws(content: str):
    changed = False

    # 1) Import stabilisieren: from .tts -> from backend.tts
    if "from .tts import" in content:
        content = content.replace("from .tts import", "from backend.tts import")
        changed = True

    # 2) sys.path Fallback einfügen (falls nicht vorhanden)
    if "ensure project root on sys.path" not in content:
        anchor = "from dotenv import load_dotenv"
        block = """import sys
from pathlib import Path as _Path

# --- ensure project root on sys.path so absolute imports always work ---
_PROJECT_ROOT = _Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))"""
        if anchor in content:
            content = content.replace(anchor, anchor + "\n" + block, 1)
            changed = True

    # 3) _handle_message: audio_start / audio_end vor else: einhängen
    if "elif message_type == 'audio_start':" not in content:
        needle = "else:\n            await self.connection_manager.send_to_client(client_id, {"
        repl = ("elif message_type == 'audio_start':\n"
                "            await self._handle_start_audio_stream(client_id, data)\n"
                "        elif message_type == 'audio_end':\n"
                "            await self._handle_end_audio_stream(client_id, data)\n"
                "        else:\n"
                "            await self.connection_manager.send_to_client(client_id, {")
        if needle in content:
            content = content.replace(needle, repl, 1)
            changed = True

    # 4) audio_ready nach audio_stream_started senden
    if "'audio_ready'" not in content and "'type': 'audio_stream_started'" in content:
        content = content.replace(
            "'timestamp': time.time()\n        })\n        \n        self.stats['audio_streams'] += 1",
            "'timestamp': time.time()\n        })\n        await self.connection_manager.send_to_client(client_id, {\n"
            "            'type': 'audio_ready',\n"
            "            'stream_id': stream_id,\n"
            "            'timestamp': time.time()\n"
            "        })\n        \n        self.stats['audio_streams'] += 1",
            1
        )
        changed = True

    # 5) _handle_text_message: ZONOS in Auswahl ergänzen
    if "elif tts_engine.lower() == \"zonos\":" not in content:
        old = (
            "        # TTS-Engine bestimmen\n"
            "        target_engine = None\n"
            "        if tts_engine:\n"
            "            if tts_engine.lower() == \"piper\":\n"
            "                target_engine = TTSEngineType.PIPER\n"
            "            elif tts_engine.lower() == \"kokoro\":\n"
            "                target_engine = TTSEngineType.KOKORO\n"
        )
        new = (
            "        # TTS-Engine bestimmen\n"
            "        target_engine = None\n"
            "        if tts_engine:\n"
            "            if tts_engine.lower() == \"piper\":\n"
            "                target_engine = TTSEngineType.PIPER\n"
            "            elif tts_engine.lower() == \"kokoro\":\n"
            "                target_engine = TTSEngineType.KOKORO\n"
            "            elif tts_engine.lower() == \"zonos\":\n"
            "                target_engine = TTSEngineType.ZONOS\n"
        )
        content = content.replace(old, new, 1)
        if content != old:
            changed = True

    # 6) default_engine-Logik um 'zonos' erweitern
    simple_line = 'default_engine = TTSEngineType.PIPER if config.default_tts_engine.lower() == "piper" else TTSEngineType.KOKORO'
    if simple_line in content:
        content = content.replace(
            simple_line,
            '_de = (config.default_tts_engine or "piper").lower()\n'
            '        if _de == "piper":\n'
            '            default_engine = TTSEngineType.PIPER\n'
            '        elif _de == "kokoro":\n'
            '            default_engine = TTSEngineType.KOKORO\n'
            '        elif _de == "zonos":\n'
            '            default_engine = TTSEngineType.ZONOS\n'
            '        else:\n'
            '            default_engine = TTSEngineType.PIPER'
        )
        changed = True

    return content, changed

def patch_fastapi(content: str):
    changed = False
    # Token an Legacy-Handler weiterreichen
    old = 'await voice_server.handle_websocket(adapter, path="/ws")'
    if old in content:
        content = content.replace(
            old,
            'path = f"/ws?token={token}" if token else "/ws"\n        await voice_server.handle_websocket(adapter, path=path)'
        )
        changed = True
    return content, changed

def patch_ttsmgr(content: str):
    changed = False
    # quick_synthesize: ZONOS zulassen
    old = ('engine_type = TTSEngineType.PIPER if engine.lower() == "piper" else TTSEngineType.KOKORO')
    if old in content:
        content = content.replace(
            old,
            'e = (engine or "piper").lower()\n'
            '        if e == "piper":\n'
            '            engine_type = TTSEngineType.PIPER\n'
            '        elif e == "kokoro":\n'
            '            engine_type = TTSEngineType.KOKORO\n'
            '        elif e == "zonos":\n'
            '            engine_type = TTSEngineType.ZONOS\n'
            '        else:\n'
            '            engine_type = TTSEngineType.PIPER'
        )
        changed = True
    return content, changed

def ensure_install_sh():
    if install_sh.exists():
        return False
    install_sh.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
echo "Installing PyTorch 2.3.1 (CUDA 12.1 wheels)..."
python - <<'PY'
import sys; print("Python:", sys.version)
