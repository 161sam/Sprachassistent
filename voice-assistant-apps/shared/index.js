// index.js – App-Bootstrap (Shared GUI)
import { DOMHelpers } from './core/dom-helpers.js';
import { sidebarManager } from './ui/sidebar.js';
import { NotificationManager } from './events.js';

const App = {
  async initializeModules() {
    await sidebarManager.initialize();
  },

  async setupApplication() {
    // Preload → Ready (falls CSS das initial versteckt)
    document.body.classList.remove('app-preload');
    document.body.classList.add('app-ready');

    // Kleiner Smoke-Test: zeigt an, dass GUI & Styles geladen sind
    const heroText = DOMHelpers.get('#va-processing-text');
    if (heroText) heroText.textContent = '„Bereit.“';
    NotificationManager.show('GUI geladen ✅', 'info', 1800);
  },

  async boot() {
    try {
      await this.initializeModules();
      await this.setupApplication();
      console.log('[BOOT] main.js initialized (all modules loaded)');
    } catch (err) {
      console.error('Application initialization failed:', err);
      NotificationManager.show('Fehler beim Laden: ' + (err?.message || err), 'error', 0);
    }
  }
};

DOMHelpers.ready(() => App.boot());
export default App;
