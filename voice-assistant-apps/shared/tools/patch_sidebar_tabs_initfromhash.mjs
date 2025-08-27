// Fügt initFromHash() hinzu und stellt kompatible Exporte bereit.
import fs from 'node:fs';
import path from 'node:path';

const FILE = 'voice-assistant-apps/shared/ui/sidebar-tabs.js';

if (!fs.existsSync(FILE)) {
  console.error('❌ Datei fehlt:', FILE);
  process.exit(1);
}

const ts = new Date().toISOString().replace(/[:.]/g,'-');
fs.copyFileSync(FILE, `${FILE}.bak_initFromHash_${ts}`);

const content = `// sidebar-tabs.js – Tab-Switching + Hash-Unterstützung
import { DOMHelpers } from '../core/dom-helpers.js';

export const sidebarTabs = {
  init() {
    const nav = DOMHelpers.get('.sidebar-nav');
    const panels = DOMHelpers.all('.sidebar-panel, [data-tab]'); // tolerant
    if (!nav || !panels.length) return;

    nav.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.sidebar-nav-item');
      if (!btn) return;
      const tab = btn.getAttribute('data-tab');
      if (!tab) return;

      // Active-Status in der Navigation
      DOMHelpers.all('.sidebar-nav-item').forEach(b => b.classList.toggle('active', b === btn));

      // Panels umschalten – Panels tragen data-tab="..."
      panels.forEach(p => {
        const match = p.getAttribute('data-tab') === tab;
        p.classList.toggle('active', match);
        // 'hidden' Flag konsistent halten (falls CSS es nutzt)
        if (match) p.removeAttribute('hidden'); else p.setAttribute('hidden','');
      });
    });
  },

  // Wird von sidebar.js beim Boot aufgerufen
  initFromHash() {
    // Basis-Init (Listener setzen)
    this.init();

    // Hash auswerten: #tab=audio  ODER  #audio
    const hash = window.location.hash || '';
    let tab = null;
    let m = hash.match(/tab=([a-z0-9_-]+)/i);
    if (!m) m = hash.match(/^#([a-z0-9_-]+)$/i);
    if (m) tab = m[1];

    if (tab) {
      const btn = DOMHelpers.get(\`.sidebar-nav-item[data-tab="\${tab}"]\`);
      if (btn) {
        // Navigation sauber triggern
        btn.click();
      }
    }
  }
};

// Kompatible Aliase für bestehenden Code
export const SidebarTabs = sidebarTabs;
export default sidebarTabs;
`;

fs.writeFileSync(FILE, content, 'utf8');
console.log('✅ sidebar-tabs.js aktualisiert: initFromHash() + kompatible Exporte hinzugefügt.');
