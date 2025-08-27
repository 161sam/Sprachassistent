// Sidebar header and panel events
import { DOMHelpers } from '../core/dom-helpers.js';
import { SidebarTabs } from './sidebar-tabs.js';
import * as Theme from './sidebar-theme.js';
import { NotificationManager } from '../events.js';

export const SidebarEvents = {
  bind() {
    const sidebar = DOMHelpers.get('#sidebar');
    const toggle = DOMHelpers.get('#sidebarToggle');
    const close = DOMHelpers.get('#sidebarClose');
    if (toggle && sidebar) toggle.addEventListener('click', () => sidebar.classList.toggle('open'));
    if (close && sidebar) close.addEventListener('click', () => sidebar.classList.remove('open'));

    const themeToggle = DOMHelpers.get('#themeToggle');
    if (themeToggle) {
      themeToggle.addEventListener('click', () => {
        if (Theme && typeof Theme.toggle === 'function') {
          Theme.toggle();
        } else {
          const el = document.documentElement;
          const next = el.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
          el.setAttribute('data-theme', next);
        }
        NotificationManager.show('Theme gewechselt', 'info', 1200);
      });
    }

    const infoToggle = DOMHelpers.get('#infoToggle');
    if (infoToggle) {
      infoToggle.addEventListener('click', () => {
        NotificationManager.show('KI-Assistent – Build OK ✅', 'info', 2500);
      });
    }

    const content = DOMHelpers.get('.sidebar-content');
    if (content) {
      content.addEventListener('change', (ev) => {
        const target = ev.target;
        if (target.id) {
          const evt = new CustomEvent('sidebar:change', { detail: { id: target.id, value: target.value } });
          document.dispatchEvent(evt);
        }
      });
      content.addEventListener('click', (ev) => {
        const btn = ev.target.closest('button');
        if (btn && btn.id) {
          const evt = new CustomEvent('sidebar:click', { detail: { id: btn.id } });
          document.dispatchEvent(evt);
        }
      });
    }

    SidebarTabs.initFromHash();
  }
};
