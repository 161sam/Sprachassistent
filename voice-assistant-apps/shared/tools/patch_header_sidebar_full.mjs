// patch_header_sidebar_full.mjs
// Ziel: "altes GUI-Aussehen" (Header + Sidebar) in der neuen modularen Struktur wiederherstellen.
// - Header nutzt Klassen aus styles.css: .top-nav, .app-logo, .nav-actions, .nav-button
// - Sidebar enthält Tabs+Panels (LLM/Audio/Themes) mit Klassen, die styles.css kennt
// - IDs für Module/Events bleiben: #sidebarToggle, #themeToggle, #infoToggle, #sidebar, #sidebarClose

import fs from 'node:fs';
import path from 'node:path';

const HTML = 'voice-assistant-apps/shared/index.html';

function read(p){ return fs.readFileSync(p, 'utf8'); }
function write(p,s){ fs.writeFileSync(p, s, 'utf8'); }
function backup(p){
  if (!fs.existsSync(p)) return null;
  const ts = new Date().toISOString().replace(/[:.]/g,'-');
  const out = `${p}.bak_hdr_sbar_full_${ts}`;
  fs.copyFileSync(p, out);
  return out;
}

// -- Header auf "altes" Markup bringen --------------------------------------
function buildHeader(){
  return `
<header class="top-nav">
  <div class="app-logo">🤖 KI-Assistent</div>
  <div class="nav-actions">
    <button id="sidebarToggle" class="nav-button" title="Einstellungen" aria-label="Einstellungen">⚙️</button>
    <button id="themeToggle" class="nav-button" title="Theme wechseln" aria-label="Theme wechseln">🌙</button>
    <button id="infoToggle" class="nav-button" title="Info" aria-label="Info">ℹ️</button>
  </div>
</header>`.trim();
}

function patchHeader(html){
  const newHeader = buildHeader();

  // Ersetze vorhandenen Header (egal ob .topbar oder .top-nav)
  const reTopbar = /<header\b[^>]*>([\s\S]*?)<\/header>/i;

  if (reTopbar.test(html)) {
    // aber nicht irgendeinen Header tief im DOM – nur den ersten im Body
    // → wir ersetzen NUR den ersten Treffer NACH <body>
    const bodyIdx = html.search(/<body[^>]*>/i);
    if (bodyIdx >= 0) {
      const before = html.slice(0, bodyIdx + html.slice(bodyIdx).match(/<body[^>]*>/i)[0].length);
      const afterArea = html.slice(bodyIdx + html.slice(bodyIdx).match(/<body[^>]*>/i)[0].length);
      const replaced = afterArea.replace(reTopbar, newHeader);
      return before + '\n' + replaced;
    }
  }

  // Kein Header gefunden → direkt nach <body> einfügen
  return html.replace(/<body[^>]*>/i, m => `${m}\n${newHeader}\n`);
}

// -- Sidebar mit Tabs+Panels befüllen ----------------------------------------
function buildSidebarInner(){
  return `
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
  </div>
  `.trim();
}

function patchSidebar(html){
  const reAside = /(<aside\b[^>]*\bid=["']sidebar["'][^>]*>)([\s\S]*?)(<\/aside>)/i;
  const inner = buildSidebarInner();

  if (reAside.test(html)) {
    return html.replace(reAside, (m, open, _inner, close) => `${open}\n${inner}\n${close}`);
  }
  // Falls kein <aside id="sidebar"> existiert → vor </body> einfügen
  const asideBlock = `<aside id="sidebar" class="sidebar">\n${inner}\n</aside>`;
  return html.replace(/<\/body>/i, `${asideBlock}\n</body>`);
}

// -- kleine Hygiene: kaputte CSP-Text-Zeile im Body entfernen ----------------
function stripBrokenCSP(html){
  return html.replace(/^\s*content="default-src[\s\S]*?">\s*$/m, '');
}

// -- Sicherstellen, dass benötigte IDs vorhanden sind ------------------------
function sanityLog(html){
  const ids = ['sidebarToggle','themeToggle','infoToggle','sidebar','sidebarClose'];
  const missing = ids.filter(id => !new RegExp(`id=["']${id}["']`).test(html));
  if (missing.length) console.warn('⚠️  Missing IDs nach Patch:', missing.join(', '));
}

// ---------------------------------------------------------------------------
(function run(){
  if (!fs.existsSync(HTML)) {
    console.error('❌ Datei nicht gefunden:', HTML);
    process.exit(1);
  }
  const bak = backup(HTML);
  if (bak) console.log('🔹 Backup erstellt:', bak);

  let html = read(HTML);

  html = patchHeader(html);
  html = patchSidebar(html);
  html = stripBrokenCSP(html);

  write(HTML, html);
  sanityLog(html);
  console.log('✅ Header & Sidebar (klassisch gestylt) eingesetzt →', HTML);
})();
