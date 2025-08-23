/* GUI Bootstrap: erzwinge Verbindung + Playback + Debug */
(function(){
  const WS_URL = "ws://127.0.0.1:48231/?token=devsecret";
  const DEFAULT_TEXT = "Hallo! Dies ist ein Staged‑TTS Test mit Intro und Hauptteil.";

  function playDataUrl(dataUrl){
    try {
      const a = new Audio();
      a.src = (dataUrl && dataUrl.startsWith('data:')) ? dataUrl : `data:audio/wav;base64,${dataUrl||''}`;
      a.preload = 'auto';
      a.oncanplaythrough = ()=> a.play().catch(err=>console.warn("[GUI] autoplay err", err));
      a.load();
    } catch(e){ console.warn('[GUI] audio play failed', e); }
  }

  // TODO-FIXED(2025-08-23): consolidated with shared VoiceAssistantCore
  async function ensureVA(){
    if (window.va) return window.va;
    if (!window.VoiceAssistantCore && !window.VoiceAssistant) {
      console.error("[GUI] VoiceAssistantCore nicht geladen.");
      return null;
    }
    const Cls = window.VoiceAssistantCore || window.VoiceAssistant;
    const va = new Cls({
      wsUrl: WS_URL,
      sampleRate: 16000,
      enableBinaryAudio: false,
      enableVAD: false
    });
    window.va = va;

    // Debug‑Hook
    const prev = va.onMessage;
    va.onMessage = (msg) => {
      console.log('[GUI] <-', msg);
      if (msg && msg.op === 'ready') {
        console.log('[GUI] READY → start_audio_stream + ping');
        va._sendMessage && va._sendMessage({type:'start_audio_stream', stream_id:'gui'});
        va._sendMessage && va._sendMessage({type:'ping', timestamp: Date.now()});
      }
      if (msg && msg.type === 'tts_chunk') {
        console.log(`[GUI] TTS_CHUNK ${msg.index+1}/${msg.total} engine=${msg.engine}`);
        playDataUrl(msg.audio);
      }
      if (msg && msg.type === 'tts_sequence_end') {
        console.log('[GUI] TTS_SEQUENCE_END', msg.sequence_id);
      }
      prev && prev(msg);
    };

    await va.initialize();
    console.log("✅ VA initialized");
    return va;
  }

  async function initUI(){
    const va = await ensureVA();
    if (!va) return;

    // Button/Textfeld verdrahten (best-effort)
    const btn  = document.querySelector('#sendTextBtn, #sendText, button[data-action="sendText"]');
    const input = document.querySelector('#textInput, #inputText, input[name="text"]');

    if (btn) {
      btn.addEventListener('click', () => {
        const txt = (input && input.value || DEFAULT_TEXT).trim();
        console.log('[GUI] sendText:', txt);
        va.sendText ? va.sendText(txt) : va._sendMessage({type:'text', content:txt});
      });
    }

    // Falls kein UI vorhanden ist: einmaligen Test schicken (nur beim ersten Start)
    if (!btn) {
      setTimeout(()=> {
        console.log('[GUI] auto test send');
        va.sendText ? va.sendText(DEFAULT_TEXT) : va._sendMessage({type:'text', content: DEFAULT_TEXT});
      }, 800);
    }
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', initUI);
  } else {
    initUI();
  }
})();


// --- live text overlay handler ---
(function(){
  const box = document.getElementById('live-text-output');
  if (!box) return;
  let lastSeq = null;
  window.addEventListener('assistant_text', ev => {
    const { sequence_id, text } = ev.detail || {};
    lastSeq = sequence_id || lastSeq || 'default';
    box.textContent = text || '';
    box.style.display = text ? 'block' : 'none';
    // auto-fade nach 12s
    if (text) {
      clearTimeout(box._hideTimer);
      box._hideTimer = setTimeout(()=>{ box.style.display='none'; }, 12000);
    }
  });
})();
