// ui/sidebar-theme.js
import { DOMHelpers } from '../core/dom-helpers.js';

export const SidebarTheme = {
  init() {
    // Theme aus localStorage laden
    const saved = this._get();
    if (saved) this.apply(saved);

    // Theme-Dropdown/Buttons binden (falls vorhanden)
    const selector = DOMHelpers.get('#themeSelector');
    if (selector) {
      selector.addEventListener('change', (e) => this.apply(e.target.value));
    }
  },

  apply(theme) {
    document.body.setAttribute('data-theme', theme);
    this._set(theme);

    // Optional: Sidebar-spezifische Elemente aktualisieren
    const icon = DOMHelpers.get('#themeToggle');
    if (icon) {
      const icons = { dark: '☀️', light: '🌙', 'sci-fi': '🚀', nature: '🌿', 'high-contrast': '🔲' };
      icon.textContent = icons[theme] || '☀️';
    }
  },

  _get() {
    try { return localStorage.getItem('va.settings.theme'); } catch { return null; }
  },
  _set(theme) {
    try { localStorage.setItem('va.settings.theme', theme); } catch {}
  }
};
