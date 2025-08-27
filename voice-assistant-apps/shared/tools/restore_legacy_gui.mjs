// restore_legacy_gui.mjs
import fs from 'node:fs';
import path from 'node:path';

const SHARED_DIR = 'voice-assistant-apps/shared';
const MONO_CANDIDATES = [
  path.join(SHARED_DIR, 'index.html.bak.base'),
  path.join(SHARED_DIR, 'index.html.monolit'),
  path.join(SHARED_DIR, 'index.html.back'),
];

const TARGET_HTML = path.join(SHARED_DIR, 'index.html');
const TARGET_CSS  = path.join(SHARED_DIR, 'styles.css');

// ---- helpers ---------------------------------------------------------------

function readFileSafe(p) {
  try { return fs.readFileSync(p, 'utf8'); } catch { return null; }
}
function writeFile(p, content) {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, content, 'utf8');
}
function backupOnce(p, label) {
  if (!fs.existsSync(p)) return;
  const ts = new Date().toISOString().replace(/[:.]/g,'-');
  const dest = `${p}.bak_restore_${label}_${ts}`;
  fs.copyFileSync(p, dest);
  return dest;
}
function extractFirstTagContent(html, tagName) {
  const re = new RegExp(`<${tagName}[^>]*>([\\s\\S]*?)<\\/${tagName}>`, 'i');
  const m = html.match(re);
  return m ? m[1] : null;
}
function removeFirstTag(html, tagName) {
  const re = new RegExp(`<${tagName}[^>]*>[\\s\\S]*?<\\/${tagName}>`, 'i');
  return html.replace(re, '');
}
function ensureMetaCSP(headHtml) {
  // Entferne kaputte freie content="..." Zeilen
  headHtml = headHtml.replace(/^\s*content="default-src[\s\S]*?">\s*$/m, '');
  // Entferne alte fehlerhafte CSP-Metas
  headHtml = headHtml.replace(/<meta[^>]+http-equiv=["']Content-Security-Policy["'][^>]*>/gi, '');

  const csp = [
    "default-src 'self'",
    "img-src 'self' data: blob:",
    "media-src 'self' blob:",
    "style-src 'self'",
    "font-src 'self' data:",
    "connect-src 'self' ws: http: https:",
    "script-src 'self'",
    "object-src 'none'",
    "base-uri 'self'"
    // 'frame-ancestors' gehört in HTTP-Header, nicht ins <meta>
  ].join('; ');
  const meta = `<meta http-equiv="Content-Security-Policy" content="${csp}">`;
  // Nach charset-Meta einfügen
  if (headHtml.includes('<meta charset')) {
    return headHtml.replace(/(<meta[^>]*charset[^>]*>\s*)/i, `$1\n  ${meta}\n`);
  }
  return `${meta}\n${headHtml}`;
}
function replaceMainContent(html, newMainInner) {
  // Ersetze INHALT von <main id="mainContent">…</main>
  const reMain = /(<main\b[^>]*id=["']mainContent["'][^>]*>)([\s\S]*?)(<\/main>)/i;
  if (reMain.test(html)) {
    return html.replace(reMain, `$1\n${newMainInner}\n$3`);
  }
  // Falls kein mainContent existiert, versuche generisches <main>
  const reGeneric = /(<main\b[^>]*>)([\s\S]*?)(<\/main>)/i;
  if (reGeneric.test(html)) {
    return html.replace(reGeneric, `$1\n${newMainInner}\n$3`);
  }
  // sonst: füge einen mainContent ein (kurz vor </body>)
  return html.replace(/<\/body>/i, `  <main id="mainContent">\n${newMainInner}\n  </main>\n</body>`);
}
function extractBodyInner(html) {
  const m = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  return m ? m[1] : null;
}
function extractHeadInner(html) {
  const m = html.match(/<head[^>]*>([\s\S]*?)<\/head>/i);
  return m ? m[1] : null;
}
function extractElementById(html, id) {
  // naive, aber robuste Extraktion eines Elements mit bestimmter id
  const re = new RegExp(
    `<([a-zA-Z0-9-]+)([^>]*\\bid=["']${id}["'][^>]*)>([\\s\\S]*?)<\\/\\1>`,
    'i'
  );
  const m = html.match(re);
  return m ? m[0] : null;
}
function gatherKnownBlocks(monolithHtml) {
  const ids = [
    'avatar',
    'processingAnimation',
    'responseContent',
    'voiceCanvas',
    'textInput',
    'voiceBtn'
  ];
  const parts = [];
  for (const id of ids) {
    const el = extractElementById(monolithHtml, id);
    if (el) parts.push(el);
  }
  if (parts.length) {
    // Behalte ungefähre alte Struktur: Hero/Center + Inputbar
    const hero = `
      <section class="va-hero">
        ${parts.filter(p => /id=["']avatar["']|id=["']processingAnimation["']|id=["']responseContent["']/i.test(p)).join('\n')}
      </section>`;
    const input = `
      <footer class="va-inputbar">
        ${parts.filter(p => /id=["']textInput["']|id=["']voiceBtn["']|id=["']voiceCanvas["']/i.test(p)).join('\n')}
      </footer>`;
    return `${hero}\n${input}`;
  }
  // Fallback: NUR Body-Inhalt
  const bodyInner = extractBodyInner(monolithHtml);
  return bodyInner || '';
}

// ---- main ------------------------------------------------------------------

function selectMonolith() {
  for (const p of MONO_CANDIDATES) {
    if (fs.existsSync(p)) return p;
  }
  throw new Error(`Keine Monolith-Datei gefunden. Erwartet eine von: \n  - ${MONO_CANDIDATES.join('\n  - ')}`);
}

(function run() {
  const monoPath = selectMonolith();
  const monoHtml = readFileSafe(monoPath);
  if (!monoHtml) throw new Error(`Kann Monolith nicht lesen: ${monoPath}`);

  const targetHtml = readFileSafe(TARGET_HTML);
  if (!targetHtml) throw new Error(`Kann Ziel-HTML nicht lesen: ${TARGET_HTML}`);

  // 1) CSS aus Monolith extrahieren
  const css = extractFirstTagContent(monoHtml, 'style');
  if (!css || css.trim().length < 20) {
    console.warn('⚠️  Konnte keinen <style>-Block im Monolithen finden – Styles könnten fehlen.');
  } else {
    const cssBackup = backupOnce(TARGET_CSS, 'precss');
    if (cssBackup) console.log(`🔹 Backup CSS -> ${cssBackup}`);
    writeFile(TARGET_CSS, css.trim() + '\n');
    console.log(`✅ Styles extrahiert -> ${TARGET_CSS}`);
  }

  // 2) CSP im HEAD reparieren
  const headInner = extractHeadInner(targetHtml) || '';
  const newHead = ensureMetaCSP(headInner);
  let html = targetHtml.replace(/<head[^>]*>[\s\S]*?<\/head>/i, `<head>\n${newHead}\n</head>`);

  // 3) Legacy-GUI in MAIN einsetzen
  let legacyMainInner = extractFirstTagContent(monoHtml, 'main');
  if (!legacyMainInner) {
    legacyMainInner = gatherKnownBlocks(monoHtml);
  }
  if (!legacyMainInner || legacyMainInner.trim().length < 10) {
    console.warn('⚠️  Konnte keinen geeigneten Main-Inhalt im Monolithen extrahieren. Lasse mainContent unverändert.');
  } else {
    html = replaceMainContent(html, legacyMainInner.trim());
    console.log('✅ Legacy-GUI in <main id="mainContent"> eingesetzt.');
  }

  // 4) sicherstellen, dass Stylesheet verlinkt ist
  if (!/href\s*=\s*["']\.\/styles\.css["']/.test(html)) {
    html = html.replace(/<\/head>/i, `  <link rel="stylesheet" href="./styles.css">\n</head>`);
  }

  // 5) kaputte freistehende CSP-Zeile im Body entfernen (falls vorhanden)
  html = html.replace(/^\s*content="default-src[\s\S]*?">\s*$/m, '');

  // 6) Datei sichern & schreiben
  const htmlBackup = backupOnce(TARGET_HTML, 'prehtml');
  if (htmlBackup) console.log(`🔹 Backup HTML -> ${htmlBackup}`);
  writeFile(TARGET_HTML, html);
  console.log(`✅ HTML aktualisiert -> ${TARGET_HTML}`);
})();

