// wire_sidebar_actions.mjs
// Verdrahtet Header-Buttons & Sidebar-Tabs und stellt Sidebar-Inhalte sicher.

import fs from 'node:fs';
import path from 'node:path';

const ROOT = 'voice-assistant-apps/shared';
const HTML = path.join(ROOT, 'index.html');
const TABS = path.join(ROOT, 'ui', 'sidebar-tabs.js');
const EVENTS = path.join(ROOT, 'ui', 'sidebar-events.js');

function read(p){ return fs.readFileSync(p,'utf8'); }
function write(p,s){ fs.writeFileSync(p,s,'utf8'); }
function backup(p,label){
  if(!fs.existsSync(p)) return null;
  const ts = new Date().toISOString().replace(/[:.]/g,'-');
  const out = `${p}.bak_${label}_${ts}`;
  fs.copyFileSync(p,out);
  console.log('🔹 Backup:', out);
  return out;
}

// --- 1) HTML: Sidebar-Inhalt sicher einsetzen --------------------------------
function ensureSidebarHtml(html){
  const reAside = /(<aside\b[^>]*\bid=["']sidebar["'][^>]*>)([\s\S]*?)(<\/aside>)/i;
  if(!reAside.test(html)) return html;

  const requiredBits = [
    'class="sidebar-header"',
    'class="sidebar-nav"',
    'class="sidebar-content"',
    'data-tab="llm"',
    'data-tab="audio"',
    'data-tab="themes"',
    'data-panel="llm"',
    'data-panel="audio"',
    'data-panel="themes"'
  ];

  const currentInner = html.match(reAside)[2] || '';
  const missing = requiredBits.filter(b => !currentInner.includes(b));
  if(missing.length === 0) {
    return html; // already ok
  }

  const sidebarInner = `
  <div class="sidebar-header">
    <h2 class="sidebar-title">Einstellungen</h2>
    <button id="sidebarClose" class="sidebar-close" aria-label="Schließen">×</button>
  </div>

  <nav class="sidebar-nav">
    <button class="sidebar-nav-item active" data-tab="llm">LLM</button>
    <button class="sidebar-nav-item" data-tab="audio">Audio</button>
    <button class="sidebar-nav-item" data-tab="themes">Themes</button>
  </nav>

  <div class="sidebar-content">
    <div class="sidebar-panel active" data-panel="llm">
      <div class="sidebar-section">
        <h3 class="sidebar-section-title">LLM-Auswahl</h3>
        <select class="sidebar-select" id="llmSelect">
          <option value="lmstudio">LM Studio</option>
          <option value="openai">OpenAI</option>
        </select>
      </div>
      <div class="sidebar-section">
        <h3 class="sidebar-section-title">System-Prompt</h3>
        <textarea class="sidebar-textarea" id="systemPrompt" rows="4" placeholder="System-Prompt…"></textarea>
      </div>
    </div>

    <div class="sidebar-panel" data-panel="audio" hidden>
      <div class="sidebar-section">
        <h3 class="sidebar-section-title">TTS-Engine</h3>
        <select class="sidebar-select" id="ttsSelect">
          <option value="piper">Piper</option>
          <option value="kokoro">Kokoro</option>
        </select>
      </div>
      <div class="sidebar-section">
        <h3 class="sidebar-section-title">Mikrofon</h3>
        <select class="sidebar-select" id="micSelect"></select>
      </div>
    </div>

    <div class="sidebar-panel" data-panel="themes" hidden>
      <div class="sidebar-section">
        <h3 class="sidebar-section-title">Theme</h3>
        <div class="theme-grid">
          <div class="theme-card theme-dark" data-theme="dark"><div class="theme-name">Dark</div></div>
          <div class="theme-card theme-light" data-theme="light"><div class="theme-name">Light</div></div>
          <div class="theme-card theme-sci-fi" data-theme="sci-fi"><div class="theme-name">Sci-Fi</div></div>
          <div class="theme-card theme-nature" data-theme="nature"><div class="theme-name">Nature</div></div>
          <div class="theme-card theme-high-contrast" data-theme="high-contrast"><div class="theme-name">High Contrast</div></div>
        </div>
      </div>
    </div>
  </div>`.trim();

  return html.replace(reAside, (m, open, _inner, close) => `${open}\n${sidebarInner}\n${close}`);
}

// --- 2) JS: Tabs schalten ----------------------------------------------------
function ensureTabsJs(code){
  // Ersetze Datei komplett durch robusten Tab-Switcher (falls nötig)
  const mustReplace =
    !/data-tab/.test(code) ||
    !/data-panel/.test(code) ||
    !/hidden/.test(code) ||
    !/export\s+const\s+sidebarTabs/.test(code);

  if(!mustReplace) return code;

  return `// sidebar-tabs.js – robustes Tab-Switching
import { DOMHelpers } from '../core/dom-helpers.js';

export const sidebarTabs = {
  init() {
    const nav = DOMHelpers.get('.sidebar-nav');
    const panels = DOMHelpers.all('.sidebar-panel');
    if (!nav || !panels.length) return;

    nav.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.sidebar-nav-item');
      if (!btn) return;
      const tab = btn.getAttribute('data-tab');
      if (!tab) return;

      // active Klasse in Nav pflegen
      DOMHelpers.all('.sidebar-nav-item').forEach(b => b.classList.toggle('active', b === btn));

      // Panels umschalten
      panels.forEach(p => {
        const match = p.getAttribute('data-panel') === tab;
        p.toggleAttribute('hidden', !match);
        p.classList.toggle('active', match);
      });
    });
  }
};

export default sidebarTabs;
`;
}

// --- 3) JS: Events binden (Theme/Info/Close/Nav) -----------------------------
function ensureEventsJs(code){
  const needReplace =
    !/themeToggle/.test(code) ||
    !/infoToggle/.test(code) ||
    !/sidebarClose/.test(code) ||
    !/export\s+const\s+sidebarEvents/.test(code);

  if(!needReplace) return code;

  return `// sidebar-events.js – bindet Header- & Sidebar-Events CSP-konform
import { DOMHelpers } from '../core/dom-helpers.js';
import { NotificationManager } from '../events.js';
import Theme from './sidebar-theme.js';
import { sidebarTabs } from './sidebar-tabs.js';

export const sidebarEvents = {
  bind() {
    // Sidebar open/close
    const sidebar = DOMHelpers.get('#sidebar');
    const toggle = DOMHelpers.get('#sidebarToggle');
    const close = DOMHelpers.get('#sidebarClose');

    if (toggle && sidebar) {
      toggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
      });
    }
    if (close && sidebar) {
      close.addEventListener('click', () => sidebar.classList.remove('open'));
    }

    // Theme toggle
    const themeToggle = DOMHelpers.get('#themeToggle');
    if (themeToggle) {
      themeToggle.addEventListener('click', () => {
        if (Theme && typeof Theme.toggle === 'function') {
          Theme.toggle();
        } else {
          // Fallback: body[data-theme] toggeln
          const el = document.documentElement;
          const next = (el.getAttribute('data-theme') === 'light') ? 'dark' : 'light';
          el.setAttribute('data-theme', next);
        }
        NotificationManager.show('Theme gewechselt', 'info', 1200);
      });
    }

    // Info
    const infoToggle = DOMHelpers.get('#infoToggle');
    if (infoToggle) {
      infoToggle.addEventListener('click', () => {
        NotificationManager.show('KI-Assistent – Build OK ✅', 'info', 2500);
      });
    }

    // Tabs initialisieren (falls noch nicht)
    sidebarTabs.init();
  }
};

export default sidebarEvents;
`;
}

// --- run ---------------------------------------------------------------------
(function run(){
  if (!fs.existsSync(HTML)) {
    console.error('❌ index.html fehlt:', HTML);
    process.exit(1);
  }

  // HTML
  const htmlSrc = read(HTML);
  backup(HTML,'html_before');
  const htmlPatched = ensureSidebarHtml(htmlSrc);
  if (htmlPatched !== htmlSrc) {
    write(HTML, htmlPatched);
    console.log('✅ Sidebar-HTML ergänzt:', HTML);
  } else {
    console.log('ℹ️ Sidebar-HTML war bereits vollständig.');
  }

  // sidebar-tabs.js
  if (fs.existsSync(TABS)) {
    const tabsSrc = read(TABS);
    const tabsPatched = ensureTabsJs(tabsSrc);
    if (tabsPatched !== tabsSrc) {
      backup(TABS,'tabs_before');
      write(TABS, tabsPatched);
      console.log('✅ Tab-Switching aktualisiert:', TABS);
    } else {
      console.log('ℹ️ Tab-Switching sah gut aus.');
    }
  } else {
    console.warn('⚠️ Datei fehlt:', TABS);
  }

  // sidebar-events.js
  if (fs.existsSync(EVENTS)) {
    const evSrc = read(EVENTS);
    const evPatched = ensureEventsJs(evSrc);
    if (evPatched !== evSrc) {
      backup(EVENTS,'events_before');
      write(EVENTS, evPatched);
      console.log('✅ Events gebunden:', EVENTS);
    } else {
      console.log('ℹ️ Events schienen bereits gebunden.');
    }
  } else {
    console.warn('⚠️ Datei fehlt:', EVENTS);
  }
})();
