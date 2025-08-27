import sys, asyncio, json, wave, numpy as np, io, base64
import websockets

def load_wav_as_int16_mono_16k(path):
    with wave.open(path, "rb") as wf:
        nchan = wf.getnchannels()
        sr = wf.getframerate()
        sw = wf.getsampwidth()
        nframes = wf.getnframes()
        raw = wf.readframes(nframes)
    if sw != 2:
        raise RuntimeError(f"Expected 16-bit PCM, got sample width={sw}")
    arr = np.frombuffer(raw, dtype=np.int16)
    if nchan > 1:
        arr = arr.reshape(-1, nchan).mean(axis=1).astype(np.int16)
    if sr != 16000:
        x_old = np.linspace(0, 1, num=len(arr), endpoint=False)
        x_new = np.linspace(0, 1, num=int(len(arr) * 16000 / sr), endpoint=False)
        arr = np.interp(x_new, x_old, arr.astype(np.float32)).astype(np.int16)
        sr = 16000
    return arr, sr

def decode_any_audio_to_int16_mono_16k(path):
    try:
        # Falls reines WAV: schnellpfad
        return load_wav_as_int16_mono_16k(path)
    except Exception:
        pass
    # Generischer Pfad via PyAV (webm/ogg/mp3/wav etc.)
    import av
    from av.audio.resampler import AudioResampler
    container = av.open(path)
    stream = next((s for s in container.streams if s.type == "audio"), None)
    if stream is None:
        raise RuntimeError("no audio stream in file")
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
    return arr_i16, 16000

async def run(uri, audio_path):
    audio, sr = decode_any_audio_to_int16_mono_16k(audio_path)
    print(f"[client] loaded audio: {audio_path}, sr={sr}, samples={len(audio)}")
    chunk_samples = 3200  # ~200ms @16k

    async with websockets.connect(uri, max_size=20_000_000) as ws:
        await ws.send(json.dumps({"op":"hello","stream_id":"smoke"}))
        print("<", await ws.recv())

        await ws.send(json.dumps({
            "type":"start_audio_stream",
            "stream_id":"smoke",
            "config":{"sampleRate":16000}
        }))

        for i in range(0, len(audio), chunk_samples):
            part = audio[i:i+chunk_samples].astype(np.int16).tobytes()
            b64 = base64.b64encode(part).decode("ascii")
            await ws.send(json.dumps({"type":"audio_chunk","stream_id":"smoke","chunk":b64}))
        await ws.send(json.dumps({"type":"end_audio_stream","stream_id":"smoke"}))

        got_resp = got_end = False
        while True:
            msg = await ws.recv()
            print("<", msg)
            try:
                payload = json.loads(msg)
                if payload.get("type") == "response":
                    got_resp = True
                if payload.get("type") == "audio_stream_ended":
                    got_end = True
            except Exception:
                pass
            if got_resp and got_end:
                break

if __name__ == "__main__":
    uri = sys.argv[1] if len(sys.argv) > 1 else "ws://127.0.0.1:48232/ws"
    audio = sys.argv[2] if len(sys.argv) > 2 else "test/example-audio.wav"
    asyncio.run(run(uri, audio))
