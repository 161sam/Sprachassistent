#!/usr/bin/env python3
import asyncio
from pathlib import Path
from backend.tts import TTSManager

async def main():
    outdir = Path("tts_out"); outdir.mkdir(exist_ok=True)
    mgr = TTSManager()
    ok = await mgr.initialize()
    if not ok:
        print("TTS-Init: keine Engine verfügbar"); return

    text = "Hallo! Dies ist ein Test der Sprachsynthese."
    results = await mgr.test_all_engines(text)

    for name, res in results.items():
        if res.success and res.audio_data:
            fn = outdir / f"test_{name}.wav"
            fn.write_bytes(res.audio_data)
            print(f"[OK] {name}: {fn} ({res.processing_time_ms:.0f} ms)")
        else:
            print(f"[FAIL] {name}: {res.error_message}")

    await mgr.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
