(() => {
  const WS_URL = "ws://127.0.0.1:48231";
  const TOKEN  = "devsecret";         // steht bei dir ohnehin so im Log
  const SAMPLE_RATE = 48000;          // passt zu TTS_OUTPUT_SR=48000

  const AC = window.AudioContext || window.webkitAudioContext;
  const ctx = new AC({ sampleRate: SAMPLE_RATE });

  let node, port;
  let ws;

  async function initAudio() {
    await ctx.audioWorklet.addModule("./audio-worklet-processor.js");
    node = new AudioWorkletNode(ctx, "audio-streaming-worklet");
    port = node.port;
    node.connect(ctx.destination);
    console.log("[StagedTTS] AudioWorklet ready");
  }

  function b64ToFloat32(b64) {
    const bin = atob(b64);
    const len = bin.length;
    const buf = new ArrayBuffer(len);
    const view = new Uint8Array(buf);
    for (let i = 0; i < len; i++) view[i] = bin.charCodeAt(i);
    return new Float32Array(buf);
  }

  function enqueueFloat32(f32, sr) {
    if (!port) return;
    if (ctx.sampleRate !== sr) {
      port.postMessage({ type: "config", sampleRate: sr });
    }
    // Transferable — vermeidet Kopie
    port.postMessage({ type: "audio", format: "f32", data: f32 }, [f32.buffer]);
  }

  async function connect() {
    await initAudio();

    const url = `${WS_URL}?token=${encodeURIComponent(TOKEN)}`;
    ws = new WebSocket(url);

    ws.addEventListener("open", () => {
      console.log("[StagedTTS] WS open");
      const sub = {
        op: "audio_subscribe",
        stream: "staged_tts",
        format: "f32",
        sampleRate: SAMPLE_RATE
      };
      ws.send(JSON.stringify(sub));
      console.log("[StagedTTS] subscribed staged_tts");
      // Autoplay entsperren
      ctx.resume().catch(()=>{});
    });

    ws.addEventListener("message", async (ev) => {
      // Wir erwarten JSON-Push (WS_TTS_PUSH_JSON=1)
      if (typeof ev.data === "string") {
        try {
          const msg = JSON.parse(ev.data);
          if (msg && msg.op === "staged_tts_chunk") {
            const sr = msg.sampleRate || SAMPLE_RATE;
            const fmt = (msg.format || "f32").toLowerCase();
            if (fmt !== "f32") return; // wir behandeln hier nur f32
            const pcm = b64ToFloat32(msg.pcm);
            enqueueFloat32(pcm, sr);
            return;
          }
          if (msg && msg.op === "staged_tts_end") {
            port && port.postMessage({ type: "flush" });
            return;
          }
        } catch (e) {
          console.warn("[StagedTTS] JSON parse error", e);
        }
      }
      // Fallback: Binary Frames könnten hier verarbeitet werden – brauchen wir nicht, da JSON erzwungen
    });

    ws.addEventListener("close", () => console.log("[StagedTTS] WS close"));
    ws.addEventListener("error", (e) => console.warn("[StagedTTS] WS error", e));
  }

  // Autostart, aber nur einmal
  if (!window.__STAGED_TTS_STARTED__) {
    window.__STAGED_TTS_STARTED__ = true;
    window.addEventListener("load", () => {
      connect().catch(err => console.error("[StagedTTS] init failed", err));
    });
  }
})();


async function playTTSChunk(msg){
  try{
    let src = msg.audio;
    if (!src && msg.audio_b64) src = "data:audio/wav;base64," + msg.audio_b64;
    if (!src) return;
    // in manchen Fällen kommt reines Base64 auch in msg.audio
    if (!src.startsWith("data:")) src = "data:audio/wav;base64," + src;
    const a = new Audio(src);
    a.play().catch(()=>{});
  }catch(e){}
}
