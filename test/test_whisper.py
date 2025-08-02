import os
from pathlib import Path
from dotenv import load_dotenv

try:
    from faster_whisper import WhisperModel  # type: ignore
except Exception as exc:  # pragma: no cover - dependency check
    raise SystemExit(f"faster-whisper import failed: {exc}")

load_dotenv()

AUDIO_FILE = Path(__file__).with_name("example-audio.wav")
if not AUDIO_FILE.exists():
    raise SystemExit(f"Audio file missing: {AUDIO_FILE}")

model_name = os.getenv("STT_MODEL", "tiny")
model_path = os.getenv("STT_MODEL_PATH")

try:
    model = WhisperModel(
        model_path or model_name,
        device=os.getenv("STT_DEVICE", "cpu"),
        compute_type=os.getenv("STT_PRECISION", "int8"),
    )
    segments, _ = model.transcribe(str(AUDIO_FILE), beam_size=1)
    text = "".join(segment.text for segment in segments).strip()
    if not text:
        raise SystemExit("Whisper produced empty transcription")
    print("Transcription:", text)
except Exception as exc:
    raise SystemExit(f"Whisper transcription failed: {exc}")
