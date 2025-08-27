// Sidebar tab switching without aliases
import { DOMHelpers } from '../core/dom-helpers.js';

export const SidebarTabs = {
  init() {
    const nav = DOMHelpers.get('.sidebar-nav');
    const panels = DOMHelpers.all('.sidebar-panel');
    if (!nav || !panels.length) return;

    nav.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.sidebar-nav-item');
      if (!btn) return;
      const tab = btn.getAttribute('data-tab');
      if (!tab) return;

      DOMHelpers.all('.sidebar-nav-item').forEach(b => b.classList.toggle('active', b === btn));
      panels.forEach(p => {
        const match = p.getAttribute('data-tab') === tab;
        p.classList.toggle('active', match);
        if (match) p.removeAttribute('hidden'); else p.setAttribute('hidden', '');
      });
    });
  },

  initFromHash() {
    this.init();
    const hash = window.location.hash || '';
    let m = hash.match(/tab=([a-z0-9_-]+)/i);
    if (!m) m = hash.match(/^#([a-z0-9_-]+)$/i);
    const tab = m ? m[1] : null;
    if (tab) {
      const btn = DOMHelpers.get(`.sidebar-nav-item[data-tab="${tab}"]`);
      if (btn) btn.click();
    }
  }
};
