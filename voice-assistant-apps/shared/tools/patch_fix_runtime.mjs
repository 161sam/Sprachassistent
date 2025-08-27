// patch_fix_runtime.mjs
// Fixes:
// 1) Remove inline styles in index.html (processing circles) -> use CSS classes
// 2) Sidebar panels: use data-tab instead of data-panel, remove 'hidden'
// 3) sidebar-events.js: import Theme as named export (no default required)

import fs from 'node:fs';
import path from 'node:path';

const ROOT = 'voice-assistant-apps/shared';
const HTML = path.join(ROOT, 'index.html');
const CSS  = path.join(ROOT, 'styles.css');
const EVTS = path.join(ROOT, 'ui', 'sidebar-events.js');

function read(p){ return fs.readFileSync(p,'utf8'); }
function write(p,s){ fs.writeFileSync(p,s,'utf8'); }
function backup(p,label){
  if (!fs.existsSync(p)) return;
  const ts = new Date().toISOString().replace(/[:.]/g,'-');
  const out = `${p}.bak_${label}_${ts}`;
  fs.copyFileSync(p,out);
  console.log('🔹 Backup:', out);
}

// --- 1) HTML: inline style entfernen + data-panel -> data-tab ---------------
function fixHtml(html) {
  let changed = false;

  // a) inline styles on processing circles -> replace with classes
  const before = html;

  // Normalize whitespace for robust replace
  let out = html
    .replace(/<div([^>]*?)class="([^"]*?\bprocessing-circle\b[^"]*?)"([^>]*?)style="[^"]*--scale:\s*1[^"]*"([^>]*)><\/div>/gi,
      '<div$1 class="$2 scale-100"$3$4></div>')
    .replace(/<div([^>]*?)class="([^"]*?\bprocessing-circle\b[^"]*?)"([^>]*?)style="[^"]*--scale:\s*0\.8[^"]*"([^>]*)><\/div>/gi,
      '<div$1 class="$2 scale-80"$3$4></div>')
    .replace(/<div([^>]*?)class="([^"]*?\bprocessing-circle\b[^"]*?)"([^>]*?)style="[^"]*--scale:\s*0\.6[^"]*"([^>]*)><\/div>/gi,
      '<div$1 class="$2 scale-60"$3$4></div>')
    // Falls noch andere style-Attr bei processing-circle existieren, entferne sie
    .replace(/(<div[^>]*class="[^"]*\bprocessing-circle\b[^"]*"[^>]*?)\sstyle="[^"]*"([^>]*>)/gi, '$1$2');

  if (out !== before) changed = true;

  // b) Sidebar Panels: data-panel -> data-tab, 'hidden' entfernen
  const reAside = /(<aside\b[^>]*\bid=["']sidebar["'][^>]*>)([\s\S]*?)(<\/aside>)/i;
  if (reAside.test(out)) {
    const inner = out.match(reAside)[2];
    let newInner = inner
      .replace(/data-panel=/gi, 'data-tab=')
      .replace(/\s(?:hidden|aria-hidden="true")/gi, '');
    if (newInner !== inner) {
      out = out.replace(reAside, (m, open, _inner, close) => `${open}\n${newInner}\n${close}`);
      changed = true;
    }
  }

  return { out, changed };
}

// --- 2) CSS: Klassen für die Scales ergänzen --------------------------------
function ensureCss(css) {
  if (/\.scale-100\b/.test(css) && /\.scale-80\b/.test(css) && /\.scale-60\b/.test(css)) {
    return { out: css, changed: false };
  }
  const add = `
/* CSP-safe processing circle scales (statt inline style="--scale: x") */
.processing-circle.scale-100 { --scale: 1; }
.processing-circle.scale-80  { --scale: 0.8; }
.processing-circle.scale-60  { --scale: 0.6; }
`.trim() + '\n';
  return { out: css + '\n' + add, changed: true };
}

// --- 3) sidebar-events.js: default-Import vermeiden -------------------------
function fixEvents(code) {
  let changed = false;
  // Replace: import Theme from './sidebar-theme.js'  ->  import * as Theme from './sidebar-theme.js';
  const out = code.replace(
    /import\s+Theme\s+from\s+['"]\.\/sidebar-theme\.js['"];?/,
    "import * as Theme from './sidebar-theme.js';"
  );
  if (out !== code) changed = true;

  // Optional robustness: Use optional chaining when calling toggle()
  const out2 = out.replace(/Theme\.toggle\(\)/g, 'Theme?.toggle?.()');
  if (out2 !== out) changed = true;

  return { out: out2, changed };
}

// --- run --------------------------------------------------------------------
(function run(){
  if (fs.existsSync(HTML)) {
    const src = read(HTML);
    const { out, changed } = fixHtml(src);
    if (changed) {
      backup(HTML, 'html_before_fix');
      write(HTML, out);
      console.log('✅ index.html: CSP-safe Kreise + data-tab Panels gesetzt.');
    } else {
      console.log('ℹ️ index.html: keine Änderungen nötig.');
    }
  } else {
    console.warn('⚠️ index.html nicht gefunden:', HTML);
  }

  if (fs.existsSync(CSS)) {
    const css = read(CSS);
    const { out, changed } = ensureCss(css);
    if (changed) {
      backup(CSS, 'css_before_fix');
      write(CSS, out);
      console.log('✅ styles.css: scale-Klassen ergänzt.');
    } else {
      console.log('ℹ️ styles.css: scale-Klassen schon vorhanden.');
    }
  } else {
    console.warn('⚠️ styles.css nicht gefunden:', CSS);
  }

  if (fs.existsSync(EVTS)) {
    const src = read(EVTS);
    const { out, changed } = fixEvents(src);
    if (changed) {
      backup(EVTS, 'events_before_fix');
      write(EVTS, out);
      console.log('✅ sidebar-events.js: Theme-Import CSP/Export-safe gemacht.');
    } else {
      console.log('ℹ️ sidebar-events.js: Import bereits kompatibel.');
    }
  } else {
    console.warn('⚠️ sidebar-events.js nicht gefunden:', EVTS);
  }
})();
