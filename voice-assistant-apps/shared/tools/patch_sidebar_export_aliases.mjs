// Fügt named Export-Aliase hinzu: SidebarEvents/SidebarTabs
import fs from 'node:fs';
import path from 'node:path';

const ROOT = 'voice-assistant-apps/shared/ui';
const FILES = [
  path.join(ROOT, 'sidebar-events.js'),
  path.join(ROOT, 'sidebar-tabs.js'),
];

function backup(p){
  if (!fs.existsSync(p)) return;
  const ts = new Date().toISOString().replace(/[:.]/g,'-');
  fs.copyFileSync(p, `${p}.bak_alias_${ts}`);
  console.log('🔹 Backup:', `${p}.bak_alias_${ts}`);
}

function ensureAlias(code, what){
  // what = 'events' | 'tabs'
  if (what === 'events') {
    // Wenn bereits SidebarEvents exportiert wird → nichts tun
    if (/export\s+(?:const|let|var)\s+SidebarEvents\b/.test(code) ||
        /export\s*\{\s*SidebarEvents\s*\}/.test(code)) return code;

    // Wenn ein Objekt sidebarEvents existiert → Alias hinzufügen
    if (/sidebarEvents\s*=\s*\{/.test(code) || /export\s+const\s+sidebarEvents\b/.test(code)) {
      // am Ende einfügen
      return code.replace(/\s*$/, `

/* alias for compatibility with sidebar.js */
export const SidebarEvents = sidebarEvents;
`);
    }
  } else if (what === 'tabs') {
    if (/export\s+(?:const|let|var)\s+SidebarTabs\b/.test(code) ||
        /export\s*\{\s*SidebarTabs\s*\}/.test(code)) return code;

    if (/sidebarTabs\s*=\s*\{/.test(code) || /export\s+const\s+sidebarTabs\b/.test(code)) {
      return code.replace(/\s*$/, `

/* alias for compatibility with sidebar.js */
export const SidebarTabs = sidebarTabs;
`);
    }
  }
  return code;
}

(function run(){
  FILES.forEach(f => {
    if (!fs.existsSync(f)) {
      console.warn('⚠️ Datei fehlt:', f);
      return;
    }
    const src = fs.readFileSync(f,'utf8');
    let out = src;

    if (f.endsWith('sidebar-events.js')) out = ensureAlias(out, 'events');
    if (f.endsWith('sidebar-tabs.js')) out = ensureAlias(out, 'tabs');

    if (out !== src) {
      backup(f);
      fs.writeFileSync(f, out, 'utf8');
      console.log('✅ Alias-Export ergänzt:', f);
    } else {
      console.log('ℹ️ Alias bereits vorhanden oder nicht nötig:', f);
    }
  });
})();
