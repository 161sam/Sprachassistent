// sidebar-events.js – bindet Header- & Sidebar-Events CSP-konform
import { DOMHelpers } from '../core/dom-helpers.js';
import { NotificationManager } from '../events.js';
import * as Theme from './sidebar-theme.js';
import { sidebarTabs } from './sidebar-tabs.js';

export const sidebarEvents = {
  bind() {
    // Sidebar open/close
    const sidebar = DOMHelpers.get('#sidebar');
    const toggle = DOMHelpers.get('#sidebarToggle');
    const close = DOMHelpers.get('#sidebarClose');

    if (toggle && sidebar) {
      toggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
      });
    }
    if (close && sidebar) {
      close.addEventListener('click', () => sidebar.classList.remove('open'));
    }

    // Theme toggle
    const themeToggle = DOMHelpers.get('#themeToggle');
    if (themeToggle) {
      themeToggle.addEventListener('click', () => {
        if (Theme && typeof Theme.toggle === 'function') {
          Theme?.toggle?.();
        } else {
          // Fallback: body[data-theme] toggeln
          const el = document.documentElement;
          const next = (el.getAttribute('data-theme') === 'light') ? 'dark' : 'light';
          el.setAttribute('data-theme', next);
        }
        NotificationManager.show('Theme gewechselt', 'info', 1200);
      });
    }

    // Info
    const infoToggle = DOMHelpers.get('#infoToggle');
    if (infoToggle) {
      infoToggle.addEventListener('click', () => {
        NotificationManager.show('KI-Assistent – Build OK ✅', 'info', 2500);
      });
    }

    // Tabs initialisieren (falls noch nicht)
    sidebarTabs.init();
  }
};

export default sidebarEvents;

/* alias for compatibility with sidebar.js */
export const SidebarEvents = sidebarEvents;
