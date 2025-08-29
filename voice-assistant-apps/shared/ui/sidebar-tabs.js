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

      // Update URL hash without scrolling/reloading
      try {
        const url = new URL(window.location.href);
        url.hash = `tab=${tab}`;
        history.replaceState(null, '', url);
      } catch (_) {}
    });
  },

  initFromHash() {
    this.init();
    const applyFromLocation = () => {
      const hash = window.location.hash || '';
      const search = window.location.search || '';
      let m = hash.match(/tab=([a-z0-9_-]+)/i);
      if (!m) m = hash.match(/^#([a-z0-9_-]+)$/i);
      if (!m) {
        const qs = new URLSearchParams(search);
        const qtab = qs.get('tab') || qs.get('section');
        if (qtab) m = [null, qtab];
      }
      const tab = m ? m[1] : null;
      if (tab) {
        const btn = DOMHelpers.get(`.sidebar-nav-item[data-tab="${tab}"]`);
        if (btn) {
          // Ensure sidebar is visible
          try { document.body.classList.add('sidebar-open'); } catch (_) {}
          // Apply tab
          btn.click();
        }
      }
    };

    applyFromLocation();
    window.addEventListener('hashchange', applyFromLocation);
  }
};
