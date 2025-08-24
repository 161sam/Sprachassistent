import asyncio
from pathlib import Path

from dotenv import load_dotenv

from ws_server.core.config import load_env

try:  # pragma: no cover - optional dependencies
    from faster_whisper import WhisperModel
except Exception as exc:  # pragma: no cover
    WhisperModel = None

from ws_server.tts.manager import TTSManager

# Minimaler End-to-End-Test des Audioflusses
# Dieser Test simuliert den Ablauf: Audio -> STT -> Intent -> TTS -> GUI.

AUDIO_FILE = Path(__file__).with_suffix('').parent / 'example-audio.wav'


async def run_pipeline():
    """Durchlaufe einfachen Audioverarbeitungs-Pfad."""
    assert AUDIO_FILE.exists(), f"Audio test file missing: {AUDIO_FILE}"

    # STT-Transkription des Audiofiles durchführen
    load_dotenv()
    load_env()
    if WhisperModel is None:
        raise RuntimeError("faster-whisper not available")
    model = WhisperModel("tiny", device="cpu")
    segments, _ = model.transcribe(str(AUDIO_FILE), beam_size=1)
    transcription = "".join(s.text for s in segments).strip()

    # Simple Intent-Erkennung
    intent = "greeting" if "hallo" in transcription.lower() else "unknown"
    response_text = f"Intent {intent} erkannt"

    # TTS-Ausgabe mit TTSManager erzeugen
    tts = TTSManager()
    await tts.initialize()
    tts_result = await tts.synthesize(response_text)

    print("Transcription:", transcription)
    print("Intent:", intent)
    print("Response Text:", response_text)
    if tts_result.success:
        print("[TTS]", len(tts_result.audio_data), "Bytes Audio erzeugt")
    else:
        print("[TTS] Fehler:", tts_result.error_message)

    # GUI/IPC Simulation
    print("[GUI] würde Antwort wiedergeben")


if __name__ == "__main__":
    asyncio.run(run_pipeline())
