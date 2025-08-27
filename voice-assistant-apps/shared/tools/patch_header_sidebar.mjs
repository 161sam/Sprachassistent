// patch_header_sidebar.mjs
import fs from 'node:fs';
import path from 'node:path';

const HTML_PATH = 'voice-assistant-apps/shared/index.html';

function read(file) { return fs.readFileSync(file, 'utf8'); }
function write(file, s) { fs.writeFileSync(file, s, 'utf8'); }
function backup(file) {
  if (!fs.existsSync(file)) return null;
  const ts = new Date().toISOString().replace(/[:.]/g,'-');
  const out = `${file}.bak_hdr_sbar_${ts}`;
  fs.copyFileSync(file, out);
  return out;
}

// Replace the whole <header class="topbar">…</header> block.
function patchHeader(html) {
  const headerNew = `
<header class="topbar">
  <div class="topbar-left">
    <button id="sidebarToggle" class="icon-button" title="Einstellungen" aria-label="Einstellungen">⚙️</button>
    <h1 class="app-title">KI-Assistent</h1>
  </div>
  <div class="topbar-right">
    <button id="themeToggle" class="icon-button" title="Theme wechseln" aria-label="Theme wechseln">🌙</button>
    <button id="infoToggle" class="icon-button" title="Info" aria-label="Info">ℹ️</button>
  </div>
</header>`.trim();

  const reHeader = /<header\b[^>]*class=["'][^"']*topbar[^"']*["'][^>]*>[\s\S]*?<\/header>/i;
  if (reHeader.test(html)) {
    return html.replace(reHeader, headerNew);
  }
  // If no header exists, inject right after <body>
  return html.replace(/<body[^>]*>/i, m => `${m}\n${headerNew}\n`);
}

// Replace the inner of <aside id="sidebar" …>…</aside> with nav+panels skeleton.
function patchSidebar(html) {
  const asideRe = /(<aside\b[^>]*\bid=["']sidebar["'][^>]*>)([\s\S]*?)(<\/aside>)/i;
  const sidebarContent = `
  <nav class="sidebar-nav">
    <button class="sidebar-nav-item" data-tab="llm">LLM</button>
    <button class="sidebar-nav-item" data-tab="audio">Audio</button>
    <button class="sidebar-nav-item" data-tab="logs">Logs</button>
  </nav>
  <section class="sidebar-panels">
    <div class="sidebar-panel" data-panel="llm">LLM Panel</div>
    <div class="sidebar-panel" data-panel="audio" hidden>Audio Panel</div>
    <div class="sidebar-panel" data-panel="logs" hidden>Logs Panel</div>
  </section>`.trim();

  if (asideRe.test(html)) {
    return html.replace(asideRe, (m, open, _inner, close) => `${open}\n${sidebarContent}\n${close}`);
  }

  // If no <aside id="sidebar"> at all, add a minimal one before </body>
  const asideBlock = `<aside id="sidebar" class="sidebar">\n${sidebarContent}\n</aside>`;
  return html.replace(/<\/body>/i, `${asideBlock}\n</body>`);
}

// Ensure the four IDs exist in DOM (safety no-op if already present)
function sanityCheck(html) {
  const ids = ['sidebarToggle','themeToggle','infoToggle','sidebar'];
  const missing = ids.filter(id => !new RegExp(`id=["']${id}["']`).test(html));
  if (missing.length) {
    console.warn('⚠️  Missing IDs after patch:', missing.join(', '));
  }
}

(function run() {
  if (!fs.existsSync(HTML_PATH)) {
    console.error('❌ Datei nicht gefunden:', HTML_PATH);
    process.exit(1);
  }
  const bak = backup(HTML_PATH);
  if (bak) console.log('🔹 Backup erstellt:', bak);

  let html = read(HTML_PATH);

  // Patch header + sidebar
  html = patchHeader(html);
  html = patchSidebar(html);

  // Optional: remove stray, broken CSP text lines in body (harmless if not present)
  html = html.replace(/^\s*content="default-src[\s\S]*?">\s*$/m, '');

  write(HTML_PATH, html);
  sanityCheck(html);
  console.log('✅ Header & Sidebar-Skelett gepatcht:', HTML_PATH);
})();
