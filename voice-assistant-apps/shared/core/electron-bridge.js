// electron-bridge.js
// Connects Electron preload events to shared UI actions

import { DOMHelpers } from './dom-helpers.js';
import { RecordingEvents, NotificationManager } from './events.js';
import { sidebarManager } from '../ui/sidebar.js';

function clearConversation() {
  const responseEl = DOMHelpers.get('#responseContent');
  if (responseEl) {
    // Show placeholder similar to AvatarManager.showResponse("")
    DOMHelpers.setHTML(responseEl, '<div class="response-empty">Ihre Antwort erscheint hier...</div>');
    DOMHelpers.toggleClass(responseEl, 'show', false);
  }
  try { NotificationManager.show('info', 'Konversation', 'Inhalt gelöscht', 1200); } catch (_) {}
}

function openSettings() {
  try { sidebarManager.open(); } catch (_) {}
  try { sidebarManager.switchTab('settings'); } catch (_) {}
  try { NotificationManager.show('info', 'Einstellungen', 'Geöffnet', 1200); } catch (_) {}
}

function openAudioSettings() {
  // Currently same as settings; can be extended to deep-link to audio section
  openSettings();
  // Focus a specific control (microphone selection)
  const mic = DOMHelpers.get('#micSelect');
  const tts = DOMHelpers.get('#ttsEngine');
  const target = mic || tts;
  if (target && typeof target.focus === 'function') {
    target.focus();
    try { target.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (_) {}
    // Temporary highlight
    const oldBox = target.style.boxShadow;
    target.style.boxShadow = '0 0 0 3px rgba(99,102,241,0.6)';
    setTimeout(() => { try { target.style.boxShadow = oldBox; } catch (_) {} }, 1200);
  }
  try { NotificationManager.show('info', 'Audio-Einstellungen', 'Fokussiert', 1200); } catch (_) {}
}

function openLlmSettings() {
  // Open sidebar and switch to LLM tab
  try { sidebarManager.open(); } catch (_) {}
  try { sidebarManager.switchTab('llm'); } catch (_) {}
  // Focus LLM controls: system prompt first, fallback to model select
  const prompt = DOMHelpers.get('#systemPrompt');
  const model = DOMHelpers.get('#llmSelect');
  const target = prompt || model;
  if (target && typeof target.focus === 'function') {
    target.focus();
    try { target.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (_) {}
    const oldBox = target.style.boxShadow;
    target.style.boxShadow = '0 0 0 3px rgba(99,102,241,0.6)';
    setTimeout(() => { try { target.style.boxShadow = oldBox; } catch (_) {} }, 1200);
  }
  try { NotificationManager.show('info', 'LLM-Einstellungen', 'Geöffnet', 1200); } catch (_) {}
}

function bindElectronEvents() {
  if (!window.electronAPI) return;

  try { window.electronAPI.onOpenSettings(() => openSettings()); } catch (_) {}
  try { window.electronAPI.onOpenAudioSettings(() => openAudioSettings()); } catch (_) {}
  try { window.electronAPI.onOpenLlmSettings(() => openLlmSettings()); } catch (_) {}
  try { window.electronAPI.onClearConversation(() => clearConversation()); } catch (_) {}
  // Recording events already raise their own notifications in RecordingEvents
  try { window.electronAPI.onStartRecording(() => RecordingEvents.startRecording()); } catch (_) {}
  try { window.electronAPI.onStopRecording(() => RecordingEvents.stopRecording()); } catch (_) {}
}

// Bind on DOM ready to ensure elements exist
DOMHelpers.ready(() => bindElectronEvents());

export { bindElectronEvents };
