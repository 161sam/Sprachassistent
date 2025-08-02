import asyncio
from pathlib import Path

# Minimaler End-to-End-Test des Audioflusses
# Dieser Test simuliert den Ablauf: Audio -> STT -> Intent -> TTS -> GUI.
# TODO: Echte STT- und Intent-Komponenten integrieren.

AUDIO_FILE = Path(__file__).with_suffix('').parent / 'example-audio.wav'

async def run_pipeline():
    assert AUDIO_FILE.exists(), f"Audio test file missing: {AUDIO_FILE}"
    # TODO: STT-Transkription des Audiofiles durchführen
    transcription = "Hallo Welt"  # placeholder
    # TODO: Intent-Erkennung / Flowise / n8n
    intent = "test_intent"
    response_text = f"Intent {intent} erkannt"
    # TODO: TTS-Ausgabe mit TTSManager erzeugen
    print("Transcription:", transcription)
    print("Intent:", intent)
    print("Response Text:", response_text)
    # GUI/IPC Simulation
    print("[GUI] würde Antwort wiedergeben")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
