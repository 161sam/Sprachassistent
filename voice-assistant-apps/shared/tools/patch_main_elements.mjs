// patch_main_elements.mjs – setzt die fehlenden Main-Elemente wieder ein
import fs from 'node:fs';
import path from 'node:path';

const ROOT = 'voice-assistant-apps/shared';
const HTML = path.join(ROOT, 'index.html');

// ------------------------------------------------------------------ helpers
const read = f => fs.readFileSync(f, 'utf8');
const write = (f, s) => fs.writeFileSync(f, s, 'utf8');
const backup = f => {
  if (!fs.existsSync(f)) return;
  const ts = new Date().toISOString().replace(/[:.]/g,'-');
  const b = `${f}.bak_main_restore_${ts}`;
  fs.copyFileSync(f, b);
  console.log('🔹 Backup:', b);
};

function ensureCSP(headHtml) {
  // kaputte freistehende content="..."-Zeile killen
  headHtml = headHtml.replace(/^\s*content="default-src[\s\S]*?">\s*$/m, '');
  // alte CSP-Metas entfernen
  headHtml = headHtml.replace(/<meta[^>]+http-equiv=["']Content-Security-Policy["'][^>]*>\s*/gi, '');
  const meta = `<meta http-equiv="Content-Security-Policy" content="default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; style-src 'self'; font-src 'self' data:; connect-src 'self' ws: http: https:; script-src 'self'; object-src 'none'; base-uri 'self'">`;
  if (/<meta[^>]*charset/i.test(headHtml)) {
    return headHtml.replace(/(<meta[^>]*charset[^>]*>\s*)/i, `$1${meta}\n`);
  }
  return `${meta}\n${headHtml}`;
}

function replaceMainInner(html, newInner) {
  const re = /(<main\b[^>]*id=["']mainContent["'][^>]*>)([\s\S]*?)(<\/main>)/i;
  if (re.test(html)) return html.replace(re, `$1\n${newInner}\n$3`);
  // Fallback: generisches <main>
  const gen = /(<main\b[^>]*>)([\s\S]*?)(<\/main>)/i;
  if (gen.test(html)) return html.replace(gen, `$1\n${newInner}\n$3`);
  // kein main vorhanden → vor </body> einfügen
  return html.replace(/<\/body>/i, `  <main id="mainContent" class="main">\n${newInner}\n  </main>\n</body>`);
}

function ensureScript(html, src, beforeSrc=null) {
  if (new RegExp(`<script[^>]+src=["']${src}["']`).test(html)) return html;
  if (beforeSrc && new RegExp(`<script[^>]+src=["']${beforeSrc}["']`).test(html)) {
    return html.replace(new RegExp(`(<script[^>]+src=["']${beforeSrc}["'][^>]*>\\s*</script>)`), `<script type="module" src="${src}"></script>\n$1`);
  }
  // sonst ans Ende des body
  return html.replace(/<\/body>/i, `  <script type="module" src="${src}"></script>\n</body>`);
}

// ------------------------------------------------------------------ main
(function run() {
  if (!fs.existsSync(HTML)) {
    console.error('❌ Datei nicht gefunden:', HTML);
    process.exit(1);
  }
  const src = read(HTML);

  // HEAD: CSP reparieren
  const headMatch = src.match(/<head[^>]*>([\s\S]*?)<\/head>/i);
  let out = src;
  if (headMatch) {
    const newHead = ensureCSP(headMatch[1]);
    out = out.replace(/<head[^>]*>[\s\S]*?<\/head>/i, `<head>\n${newHead}\n</head>`);
  }

  // MAIN: fehlende GUI-Elemente einsetzen (aus bak.base übernommen, ohne Inline-Events)
  const mainInner = `
    <section class="avatar-section">
      <div class="avatar idle style-default" id="avatar">
        <!-- Voice Visualization Canvas -->
        <canvas class="voice-visualizer" id="voiceCanvas" width="400" height="400"></canvas>

        <div class="avatar-nebel">
          <div class="nebel-layer"></div>
          <div class="nebel-layer"></div>
          <div class="nebel-layer"></div>
        </div>
        <div class="avatar-core" title="Klicken für Interaktion"></div>

        <!-- Processing Animation -->
        <div class="processing-animation" id="processingAnimation">
          <div class="processing-circle" style="--scale: 1"></div>
          <div class="processing-circle" style="--scale: 0.8"></div>
          <div class="processing-circle" style="--scale: 0.6"></div>
        </div>

        <!-- Response Overlay -->
        <div class="response-overlay">
          <div class="response-content" id="responseContent">
            <div class="response-empty">Ihre Antwort erscheint hier...</div>
          </div>
        </div>
      </div>
    </section>

    <div class="input-container">
      <input
        type="text"
        id="textInput"
        class="text-input"
        placeholder="Fragen Sie mich etwas..."
        autocomplete="off"
        autocorrect="off"
        autocapitalize="sentences"
      />
      <button class="action-button" id="sendBtn" title="Senden" type="button">➤</button>
      <button class="action-button voice" id="voiceBtn" title="Spracheingabe" type="button">
        <span id="voiceIcon">🎤</span>
      </button>
      <div class="recording-indicator" id="recordingIndicator">
        <div class="recording-dot"></div>
        <span>Aufnahme läuft... <span id="recordingTime">0s</span></span>
      </div>
    </div>
  `.replace(/\n[ ]{2,}/g, '\n  ').trim();

  backup(HTML);
  out = replaceMainInner(out, mainInner);

  // SCRIPT: sicherstellen, dass main.js geladen wird (Bootstrap importiert core/*)
  out = ensureScript(out, './main.js', './index.js');

  // Doppelte/kaputte freistehende CSP-Zeile im Body tilgen (falls vorhanden)
  out = out.replace(/^\s*content="default-src[\s\S]*?">\s*$/m, '');

  write(HTML, out);
  console.log('✅ MAIN-Elemente wiederhergestellt & CSP bereinigt:', HTML);

  // Bonus: Notification onclick aus core/events.js → EventListener (CSP)
  const coreEvents = path.join(ROOT, 'core', 'events.js');
  const altEvents  = path.join(ROOT, 'events.js');
  [coreEvents, altEvents].forEach(p => {
    if (!fs.existsSync(p)) return;
    let s = read(p);
    const before = s;
    // 1) onclick entfernen
    s = s.replace(
      /<button class="notification-close"[^>]*onclick="NotificationManager\.close\(this\)"[^>]*>×<\/button>/,
      '<button class="notification-close" type="button" aria-label="Schließen">×</button>'
    );
    // 2) Listener nach append() registrieren (nur einmal einfügen)
    s = s.replace(
      /container\.appendChild\(notification\);\s*\n/,
      `container.appendChild(notification);\n    const closeBtn = notification.querySelector('.notification-close');\n    if (closeBtn) closeBtn.addEventListener('click', () => NotificationManager.close(closeBtn));\n`
    );
    if (s !== before) {
      backup(p);
      write(p, s);
      console.log('✅ CSP: Notification-Close auf EventListener umgestellt →', p);
    }
  });
})();
