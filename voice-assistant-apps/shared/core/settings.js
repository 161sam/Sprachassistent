// settings.js – Sidebar settings binding and backend wiring
import { DOMHelpers } from './dom-helpers.js';
import Backend, { HttpManager, WebSocketManager } from './backend.js';
import AudioManager, { TTSPlayer } from './audio.js';

const LS_PREFIX = 'va.settings.';
const PROMPTS_KEY = 'va.prompts.json';

const SettingsState = {
  sttModel: 'base',
  ttsEngine: 'piper',
  ttsVoice: 'de-thorsten-low',
  ttsLanguage: 'de-DE',
  ttsSpeed: 0.92,
  ttsVolume: 1.0,

  avatarStyle: 'default',
  voiceVisualization: true,
  noiseSuppression: true,
  echoCancellation: true,

  stagedTtsEnabled: true,
  introEngine: 'auto',
  mainEngine: 'auto',
  introLength: 80,
  crossfadeMs: 60,
  chunkedOutput: true,
  chunkSizeMin: 100,
  chunkSizeMax: 220,
  mainMaxChunks: 6,

  wsHost: '127.0.0.1',
  wsPort: '48232',
  wsToken: 'devsecret',
  micDeviceId: '',

  llmModel: '',
  llmTemperature: 0.7,
  llmMaxTokens: 256,
  systemPrompt: 'default',
  systemPromptText: '',
  sttLanguage: 'de',

  autoDarkMode: false,
  showAvatar: true,
  reducedMotion: false,
};

function loadSettings() {
  try {
    Object.keys(SettingsState).forEach((k) => {
      const v = localStorage.getItem(LS_PREFIX + k);
      if (v === null) return;
      if (typeof SettingsState[k] === 'boolean') SettingsState[k] = v === 'true';
      else if (typeof SettingsState[k] === 'number') SettingsState[k] = Number(v);
      else SettingsState[k] = v;
    });
    // Fallbacks for connection settings from unprefixed keys
    ['wsHost','wsPort','wsToken'].forEach((k) => {
      if (!localStorage.getItem(LS_PREFIX + k)) {
        const raw = localStorage.getItem(k);
        if (raw) SettingsState[k] = raw;
      }
    });
  } catch (_) {}
}

function saveSetting(key, value) {
  try { localStorage.setItem(LS_PREFIX + key, String(value)); } catch (_) {}
}

function loadPrompts() {
  try {
    const raw = localStorage.getItem(PROMPTS_KEY);
    if (raw) return JSON.parse(raw);
  } catch (_) {}
  // Defaults
  return {
    default: 'You are a helpful assistant. Answer concisely and speak naturally.',
    helpful: 'Handle tasks helpfully and politely. Prefer spoken style sentences.',
    creative: 'Be imaginative but clear. Avoid lists, use natural speech.',
    professional: 'Be concise, correct, and neutral. No markdown.',
    casual: 'Keep it friendly and conversational. Use short sentences.',
  };
}

function savePrompts(prompts) {
  try { localStorage.setItem(PROMPTS_KEY, JSON.stringify(prompts)); } catch (_) {}
}

function setRangeValue(id, value, suffix = '') {
  const span = DOMHelpers.get('#' + id + 'Value');
  if (!span) return;
  span.textContent = suffix ? String(value) + suffix : String(value);
}

function applyToUI() {
  // Basic selects / inputs
  [
    'sttModel','ttsEngine','ttsVoice','ttsLanguage','avatarStyle','introEngine','mainEngine',
    'wsHost','wsPort','wsToken','llmModel','micDeviceId','sttLanguage',
    'llmProvider','llmApiBase','llmApiKey'
  ].forEach((id) => {
    const el = DOMHelpers.get('#' + id);
    if (el && typeof SettingsState[id] !== 'undefined') {
      try { el.value = SettingsState[id]; } catch (_) {}
    }
  });

  const ttsSpeed = DOMHelpers.get('#ttsSpeed');
  if (ttsSpeed) { ttsSpeed.value = String(SettingsState.ttsSpeed); setRangeValue('ttsSpeed', SettingsState.ttsSpeed, 'x'); }
  const ttsVolume = DOMHelpers.get('#ttsVolume');
  if (ttsVolume) { ttsVolume.value = String(SettingsState.ttsVolume); setRangeValue('ttsVolume', SettingsState.ttsVolume); }
  const introLength = DOMHelpers.get('#introLength');
  if (introLength) { introLength.value = String(SettingsState.introLength); setRangeValue('introLength', SettingsState.introLength); }
  const crossfade = DOMHelpers.get('#crossfadeMs');
  if (crossfade) { crossfade.value = String(SettingsState.crossfadeMs); setRangeValue('crossfadeMs', SettingsState.crossfadeMs, 'ms'); }
  const cmin = DOMHelpers.get('#chunkSizeMin');
  if (cmin) { cmin.value = String(SettingsState.chunkSizeMin); setRangeValue('chunkSizeMin', SettingsState.chunkSizeMin); }
  const cmax = DOMHelpers.get('#chunkSizeMax');
  if (cmax) { cmax.value = String(SettingsState.chunkSizeMax); setRangeValue('chunkSizeMax', SettingsState.chunkSizeMax); }
  const mmc = DOMHelpers.get('#mainMaxChunks');
  if (mmc) { mmc.value = String(SettingsState.mainMaxChunks); setRangeValue('mainMaxChunks', SettingsState.mainMaxChunks); }
  const llmTemp = DOMHelpers.get('#llmTemperature');
  if (llmTemp) { llmTemp.value = String(SettingsState.llmTemperature); setRangeValue('llmTemperature', SettingsState.llmTemperature); }
  const llmMax = DOMHelpers.get('#llmMaxTokens');
  if (llmMax) { llmMax.value = String(SettingsState.llmMaxTokens); setRangeValue('llmMaxTokens', SettingsState.llmMaxTokens); }

  const prov = DOMHelpers.get('#llmProvider'); if (prov) prov.value = SettingsState.llmProvider || 'lmstudio';
  const base = DOMHelpers.get('#llmApiBase'); if (base) base.value = SettingsState.llmApiBase || 'http://127.0.0.1:1234/v1';
  const key = DOMHelpers.get('#llmApiKey'); if (key) key.value = SettingsState.llmApiKey || '';
  const sysTxt = DOMHelpers.get('#systemPromptText'); if (sysTxt) sysTxt.value = SettingsState.systemPromptText || '';
  // Populate presets
  const presets = loadPrompts();
  const presetSel = DOMHelpers.get('#systemPromptPreset');
  if (presetSel) {
    presetSel.innerHTML = '';
    Object.keys(presets).forEach((name) => {
      const opt = document.createElement('option');
      opt.value = name; opt.textContent = name;
      presetSel.appendChild(opt);
    });
    // Select default if none stored
    const current = localStorage.getItem(LS_PREFIX + 'systemPromptPreset') || 'default';
    presetSel.value = presets[current] ? current : 'default';
    if (sysTxt && presets[presetSel.value]) sysTxt.value = presets[presetSel.value];
  }

  // Toggles (button.sidebar-toggle uses .active)
  [ 'voiceVisualization','noiseSuppression','echoCancellation','stagedTtsEnabled','autoDarkMode','showAvatar','reducedMotion' ]
    .concat(['chunkedOutput'])
    .forEach((id) => {
      const el = DOMHelpers.get('#' + id);
      if (el) DOMHelpers.toggleClass(el, 'active', !!SettingsState[id]);
    });
}

function populateLlmModels(models, current) {
  const select = DOMHelpers.get('#llmModel');
  if (!select) return;
  select.innerHTML = '';
  if (!models || models.length === 0) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'Keine Modelle gefunden';
    select.appendChild(opt);
    return;
  }
  models.forEach((m) => {
    const opt = document.createElement('option');
    opt.value = m;
    opt.textContent = m;
    select.appendChild(opt);
  });
  select.value = current || models[0];
  SettingsState.llmModel = select.value;
}

async function refreshLlmModels() {
  try {
    const models = await HttpManager.getLlmModels();
    populateLlmModels(models, SettingsState.llmModel);
  } catch (e) {
    console.warn('LLM Models refresh error:', e?.message || e);
  }
}

function applyThemeToggles() {
  try {
    document.body.classList.toggle('reduced-motion', !!SettingsState.reducedMotion);
    const avatar = DOMHelpers.get('#avatar');
    if (avatar) avatar.style.display = SettingsState.showAvatar ? '' : 'none';
  } catch (_) {}
}

function maybeAutoDarkMode() {
  if (!SettingsState.autoDarkMode) return;
  try {
    const hour = new Date().getHours();
    const shouldBeDark = hour < 7 || hour > 19;
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = shouldBeDark ? 'dark' : 'light';
    if (current !== next) document.documentElement.setAttribute('data-theme', next);
  } catch (_) {}
}

function reconnectBackendIfNeeded() {
  // Close and re-init to apply wsHost/wsPort/token
  try { Backend.shutdown(); } catch (_) {}
  try { Backend.init({}); } catch (_) {}
}

function onSettingChanged(id, value) {
  // Normalize numbers/booleans
  const numericRanges = new Set(['ttsSpeed','introLength','crossfadeMs','llmTemperature','llmMaxTokens']);
  if (numericRanges.has(id)) value = Number(value);
  SettingsState[id] = value;
  saveSetting(id, value);

  switch (id) {
    case 'ttsEngine':
      WebSocketManager.sendMessage({ type: 'switch_tts_engine', engine: value });
      break;
    case 'ttsVoice':
      WebSocketManager.sendMessage({ type: 'set_tts_voice', voice: value });
      break;
    case 'ttsLanguage':
      WebSocketManager.sendMessage({ type: 'set_tts_language', value: value });
      break;
    case 'ttsSpeed':
      setRangeValue('ttsSpeed', value, 'x');
      // Geschwindigkeitsänderung nur an Backend melden – Player manipuliert playbackRate nicht.
      WebSocketManager.sendMessage({ type: 'set_tts_options', speed: value });
      break;
    case 'ttsVolume':
      setRangeValue('ttsVolume', value);
      if (typeof AudioManager !== 'undefined' && AudioManager.setTtsVolume) {
        AudioManager.setTtsVolume(value);
      }
      WebSocketManager.sendMessage({ type: 'set_tts_options', volume: value });
      break;
    case 'sttModel':
      // Saved for next handshake; notify user
      console.log('STT Modell gesetzt:', value);
      break;
    case 'introLength':
      setRangeValue('introLength', value);
      break;
    case 'crossfadeMs':
      setRangeValue('crossfadeMs', value, 'ms');
      if (AudioManager?.setCrossfadeDuration) AudioManager.setCrossfadeDuration(value);
      else if (TTSPlayer?.setCrossfadeDuration) TTSPlayer.setCrossfadeDuration(value);
      break;
    case 'chunkSizeMin': setRangeValue('chunkSizeMin', value); break;
    case 'chunkSizeMax': setRangeValue('chunkSizeMax', value); break;
    case 'mainMaxChunks': setRangeValue('mainMaxChunks', value); break;
    case 'llmTemperature':
      setRangeValue('llmTemperature', value);
      WebSocketManager.sendMessage({ type: 'set_llm_options', temperature: value });
      break;
    case 'llmMaxTokens':
      setRangeValue('llmMaxTokens', value);
      WebSocketManager.sendMessage({ type: 'set_llm_options', max_tokens: value });
      break;
    case 'systemPromptText':
      if ((SettingsState.systemPrompt || '') === 'custom') {
        WebSocketManager.sendMessage({ type: 'set_llm_options', system_prompt: value });
      } else {
        WebSocketManager.sendMessage({ type: 'set_llm_options', system_prompt: value });
      }
      break;
    case 'systemPromptPreset': {
      const presets = loadPrompts();
      const val = String(value || 'default');
      try { localStorage.setItem(LS_PREFIX + 'systemPromptPreset', val); } catch (_) {}
      const sys = DOMHelpers.get('#systemPromptText');
      if (sys && presets[val]) sys.value = presets[val];
      WebSocketManager.sendMessage({ type: 'set_llm_options', system_prompt: (presets[val] || '') });
      break; }
    case 'llmProvider':
    case 'llmApiBase':
    case 'llmApiKey': {
      const provider = (DOMHelpers.get('#llmProvider')?.value || 'lmstudio');
      const api_base = DOMHelpers.get('#llmApiBase')?.value || '';
      const api_key = DOMHelpers.get('#llmApiKey')?.value || '';
      SettingsState.llmProvider = provider; SettingsState.llmApiBase = api_base; SettingsState.llmApiKey = api_key;
      saveSetting('llmProvider', provider); saveSetting('llmApiBase', api_base); saveSetting('llmApiKey', api_key);
      WebSocketManager.sendMessage({ type: 'set_llm_provider', provider, api_base, api_key });
      break; }
    case 'llmModel':
      WebSocketManager.sendMessage({ type: 'switch_llm_model', model: value });
      break;
    case 'sttLanguage':
      WebSocketManager.sendMessage({ type: 'set_stt_options', language: value });
      break;
    case 'wsHost': case 'wsPort': case 'wsToken':
      // Also persist to unprefixed keys expected elsewhere
      try { localStorage.setItem(id, String(value)); } catch (_) {}
      if (id === 'wsToken') try { localStorage.setItem('voice_auth_token', value); } catch (_) {}
      reconnectBackendIfNeeded();
      break;
    case 'avatarStyle':
      // reserved for future styles
      break;
    default:
      break;
  }
}

function onToggle(id) {
  const el = DOMHelpers.get('#' + id);
  const active = el?.classList?.contains('active');
  SettingsState[id] = !!active;
  saveSetting(id, SettingsState[id]);

  switch (id) {
    case 'voiceVisualization':
    case 'noiseSuppression':
    case 'echoCancellation':
      // used by AudioManager.startRecording
      break;
    case 'stagedTtsEnabled':
      break;
    case 'chunkedOutput':
      WebSocketManager.sendMessage({ type: 'staged_tts_control', chunked: !!SettingsState.chunkedOutput });
      break;
    case 'autoDarkMode':
    case 'showAvatar':
    case 'reducedMotion':
      applyThemeToggles();
      break;
  }
}

function bindEvents() {
  document.addEventListener('sidebar:change', (ev) => {
    const { id, value } = ev.detail || {};
    if (!id) return;
    onSettingChanged(id, value);
  });
  document.addEventListener('sidebar:click', (ev) => {
    const { id } = ev.detail || {};
    if (!id) return;

    // Toggle buttons
    if (['voiceVisualization','noiseSuppression','echoCancellation','stagedTtsEnabled','autoDarkMode','showAvatar','reducedMotion','chunkedOutput'].includes(id)) {
      const el = DOMHelpers.get('#' + id);
      if (el) {
        el.classList.toggle('active');
        onToggle(id);
      }
      return;
    }

    if (id === 'applyTtsPlan') {
      const btn = DOMHelpers.get('#applyTtsPlan');
      if (btn) btn.disabled = true;
      const status = DOMHelpers.get('#ttsPlanStatus');
      if (status) status.textContent = 'Übernehme…';
      WebSocketManager.sendMessage({
        type: 'staged_tts_control',
        enabled: !!SettingsState.stagedTtsEnabled,
        intro_engine: SettingsState.introEngine,
        main_engine: SettingsState.mainEngine,
        intro_length: Number(SettingsState.introLength),
        crossfade_ms: Number(SettingsState.crossfadeMs),
        chunked: !!SettingsState.chunkedOutput,
        chunk_size_min: Number(SettingsState.chunkSizeMin),
        chunk_size_max: Number(SettingsState.chunkSizeMax),
        main_max_chunks: Number(SettingsState.mainMaxChunks)
      });
      if (status) status.textContent = 'Plan gesendet…';
    }
    if (id === 'refreshLlmModels') refreshLlmModels();
    if (id === 'testStagedTTS') {
      const sample = 'Das ist ein Test für gestufte Sprachsynthese mit einer längeren Passage, um den Übergang zu prüfen.';
      try { window.Backend.sendText(sample); } catch (_) {}
    }
    if (id === 'testConnection') {
      const el = DOMHelpers.get('#connectionStatus');
      HttpManager.healthCheck().then((ok) => {
        if (el) el.textContent = ok ? 'Verbunden' : 'Fehler';
      }).catch((e) => { if (el) el.textContent = 'Fehler'; console.warn('Health error', e?.message || e); });
    }
    if (id === 'saveSystemPrompt') {
      const nameEl = DOMHelpers.get('#systemPromptName');
      const textEl = DOMHelpers.get('#systemPromptText');
      const name = (nameEl?.value || '').trim();
      const text = (textEl?.value || '').trim();
      if (!name || !text) return;
      const presets = loadPrompts();
      presets[name] = text; savePrompts(presets);
      const sel = DOMHelpers.get('#systemPromptPreset');
      if (sel) {
        const opt = document.createElement('option'); opt.value = name; opt.textContent = name; sel.appendChild(opt); sel.value = name;
      }
      try { localStorage.setItem(LS_PREFIX + 'systemPromptPreset', name); } catch(_) {}
      WebSocketManager.sendMessage({ type: 'set_llm_options', system_prompt: text });
    }
  });

  // Range live update on input
  ['ttsSpeed','introLength','crossfadeMs','llmTemperature','llmMaxTokens'].forEach((id) => {
    const el = DOMHelpers.get('#' + id);
    if (el) el.addEventListener('input', () => onSettingChanged(id, el.value));
  });
  const ttsVol = DOMHelpers.get('#ttsVolume');
  if (ttsVol) ttsVol.addEventListener('input', () => onSettingChanged('ttsVolume', ttsVol.value));
  const cminEl = DOMHelpers.get('#chunkSizeMin'); if (cminEl) cminEl.addEventListener('input', () => onSettingChanged('chunkSizeMin', cminEl.value));
  const cmaxEl = DOMHelpers.get('#chunkSizeMax'); if (cmaxEl) cmaxEl.addEventListener('input', () => onSettingChanged('chunkSizeMax', cmaxEl.value));
  const mmcEl = DOMHelpers.get('#mainMaxChunks'); if (mmcEl) mmcEl.addEventListener('input', () => onSettingChanged('mainMaxChunks', mmcEl.value));
  const presetSel = DOMHelpers.get('#systemPromptPreset');
  if (presetSel) presetSel.addEventListener('change', () => onSettingChanged('systemPromptPreset', presetSel.value));

  // Mic device selection
  const mic = DOMHelpers.get('#micSelect');
  if (mic) mic.addEventListener('change', () => onSettingChanged('micDeviceId', mic.value));

  // Custom prompt text input
  const sysTxt2 = DOMHelpers.get('#systemPromptText');
  if (sysTxt2) sysTxt2.addEventListener('input', () => onSettingChanged('systemPromptText', sysTxt2.value));
}

export const Settings = {
  async init() {
    loadSettings();
    applyToUI();
    bindEvents();
    applyThemeToggles();
    maybeAutoDarkMode();
    // initial models list
    try { await refreshLlmModels(); } catch (_) {}
    // populate microphones
    try {
      if (navigator.mediaDevices?.enumerateDevices) {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const mics = devices.filter((d) => d.kind === 'audioinput');
        const sel = DOMHelpers.get('#micSelect');
        if (sel) {
          sel.innerHTML = '';
          mics.forEach((d) => {
            const opt = document.createElement('option');
            opt.value = d.deviceId || '';
            opt.textContent = d.label || `Mic ${sel.length + 1}`;
            sel.appendChild(opt);
          });
          if (SettingsState.micDeviceId) sel.value = SettingsState.micDeviceId;
        }
      }
    } catch (_) {}

    // Audio Input Test bindings
    try {
      const startBtn = DOMHelpers.get('#startAudioTest');
      const stopBtn = DOMHelpers.get('#stopAudioTest');
      const canvas = DOMHelpers.get('#audioTestCanvas');
      const ctx = canvas ? canvas.getContext('2d') : null;
      let anim = 0; let stream = null; let analyser = null; let ac = null; let source = null;

      async function startTest() {
        try {
          ac = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
          const constraints = { audio: { deviceId: SettingsState.micDeviceId ? { exact: SettingsState.micDeviceId } : undefined, noiseSuppression: SettingsState.noiseSuppression !== false, echoCancellation: SettingsState.echoCancellation !== false } };
          stream = await navigator.mediaDevices.getUserMedia(constraints);
          source = ac.createMediaStreamSource(stream);
          analyser = ac.createAnalyser(); analyser.fftSize = 1024; analyser.smoothingTimeConstant = 0.8; source.connect(analyser);
          const data = new Uint8Array(analyser.frequencyBinCount);
          function draw() {
            if (!ctx || !analyser) return;
            analyser.getByteTimeDomainData(data);
            ctx.clearRect(0,0,canvas.width,canvas.height);
            ctx.strokeStyle = '#8ab4f8'; ctx.lineWidth = 2; ctx.beginPath();
            const slice = canvas.width / data.length; let x = 0;
            for (let i=0;i<data.length;i++){ const v = (data[i]-128)/128; const y = (canvas.height/2) + v*(canvas.height/2-5); if (i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y); x+=slice; }
            ctx.stroke();
            // VAD threshold line
            const thr = parseFloat(DOMHelpers.get('#vadThreshold')?.value || '0.01');
            DOMHelpers.get('#vadThresholdValue') && (DOMHelpers.get('#vadThresholdValue').textContent = thr.toFixed(3));
            ctx.strokeStyle = 'rgba(245,158,11,0.8)'; ctx.setLineDash([4,3]); ctx.beginPath();
            const yThr = (canvas.height/2) - (thr*(canvas.height/2-5)); ctx.moveTo(0,yThr); ctx.lineTo(canvas.width,yThr); ctx.stroke(); ctx.setLineDash([]);
            anim = requestAnimationFrame(draw);
          }
          draw();
        } catch(e) { console.warn('Audio test start failed:', e); }
      }
      function stopTest(){ try { if (anim) cancelAnimationFrame(anim); anim=0; } catch(_){}; try { if (stream) stream.getTracks().forEach(t=>t.stop()); } catch(_){}; try { if (ac) ac.close(); } catch(_){}; stream=null; ac=null; analyser=null; source=null; if (ctx) { ctx.clearRect(0,0,canvas.width,canvas.height); } }
      startBtn && startBtn.addEventListener('click', startTest);
      stopBtn && stopBtn.addEventListener('click', stopTest);
      const vad = DOMHelpers.get('#vadThreshold'); vad && vad.addEventListener('input', () => { /* visual only */ });
    } catch(_) {}
  },
  get(key) { return SettingsState[key]; }
};

// Auto-init on DOM ready
DOMHelpers.ready(() => Settings.init());

export default Settings;
