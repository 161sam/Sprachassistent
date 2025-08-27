# backend/ws-server/tts/engines.zonos.py
import os, asyncio, numpy as np, torch, torchaudio
from zonos.model import Zonos
from zonos.conditioning import make_cond_dict

TARGET_SR = int(os.getenv("TTS_OUTPUT_SR", "48000"))  # 48k ist im Browser am dankbarsten
DEFAULT_LANG = os.getenv("ZONOS_LANG", "de-de")
DEFAULT_MODEL = os.getenv("ZONOS_MODEL", "Zyphra/Zonos-v0.1-transformer")  # oder -hybrid

def _pcm16(y: np.ndarray) -> bytes:
    y = np.clip(y, -1.0, 1.0)
    return (y * 32767.0).astype(np.int16).tobytes()

class ZonosTTSEngine:
    engine_type = "zonos"
    name = "Zonos v0.1"

    def __init__(self, device=None, model_id=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = Zonos.from_pretrained(model_id or DEFAULT_MODEL, device=self.device)
        self.spk_cache = {}  # voice_name -> embedding (cache)

    def _load_speaker(self, voice: str):
        # voice darf Dateipfad oder Kurzname (-> spk_cache/<name>.wav) sein
        path = voice if os.path.exists(voice) else os.path.join("spk_cache", f"{voice}.wav")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Speaker file not found: {path}")
        wav, sr = torchaudio.load(path)  # [C,T]
        emb = self.model.make_speaker_embedding(wav.to(self.device), sr)
        return emb

    def _speaker(self, voice: str):
        if voice not in self.spk_cache:
            self.spk_cache[voice] = self._load_speaker(voice)
        return self.spk_cache[voice]

    def synth(self, text: str, voice: str, language: str = DEFAULT_LANG,
              speed: float = 1.0, pitch: float = 0.0, emotion: str | None = None,
              audio_prefix_path: str | None = None):
        # Optionaler Audio-Prefix für Stil/Whispering usw.
        audio_prefix = None
        if audio_prefix_path and os.path.exists(audio_prefix_path):
            ap_wav, ap_sr = torchaudio.load(audio_prefix_path)
            audio_prefix = (ap_wav.to(self.device), ap_sr)

        spk = self._speaker(voice)
        cond_dict = make_cond_dict(
            text=text, speaker=spk, language=language,
            speed=speed, pitch=pitch, emotion=emotion,
            audio_prefix=audio_prefix
        )
        conditioning = self.model.prepare_conditioning(cond_dict)
        codes = self.model.generate(conditioning)
        wav = self.model.autoencoder.decode(codes).cpu()[0]  # [T]
        sr = self.model.autoencoder.sampling_rate  # 44100

        # Auf Browsersample-Rate bringen (48k empfohlen)
        if TARGET_SR and sr != TARGET_SR:
            wav = torchaudio.functional.resample(wav.unsqueeze(0), sr, TARGET_SR).squeeze(0)
            sr = TARGET_SR
        return sr, wav.numpy()

    async def stream_ws(self, ws, **kwargs):
        sr, y = self.synth(**kwargs)
        frame = int(sr * 0.02)  # ~20ms Frames
        seq = 0
        for i in range(0, len(y), frame):
            chunk = y[i:i+frame]
            await ws.send_json({
                "type": "audio-chunk",
                "seq": seq,
                "sample_rate": sr,
                "pcm16": _pcm16(chunk).hex()
            })
            seq += 1
            await asyncio.sleep(0)  # Cooperative scheduling
        await ws.send_json({"type": "audio-end"})
