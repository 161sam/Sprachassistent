// main.js – Module Bootstrap (CSP-safe)
(async () => {
  try {
    const ok = (name, p) => console.log('[BOOT] OK:', name, `(${p})`);
    const fail = (name, p, e) => console.error('[BOOT] FAILED importing', name, `(${p}) →`, e);

    await import('./core/dom-helpers.js').then(()=>ok('dom-helpers','./core/dom-helpers.js')).catch(e=>fail('dom-helpers','./core/dom-helpers.js',e));
    await import('./core/backend.js').then(()=>ok('backend','./core/backend.js')).catch(e=>fail('backend','./core/backend.js',e));
    await import('./core/audio.js').then(()=>ok('audio','./core/audio.js')).catch(e=>fail('audio','./core/audio.js',e));
    await import('./core/events.js').then(()=>ok('events','./core/events.js')).catch(e=>fail('events','./core/events.js',e));

    await import('./ui/sidebar.js').then(()=>ok('sidebar','./ui/sidebar.js')).catch(e=>fail('sidebar','./ui/sidebar.js',e));
    await import('./ui/hotkeys.js').then(()=>ok('hotkeys','./ui/hotkeys.js')).catch(e=>fail('hotkeys','./ui/hotkeys.js',e));
    await import('./core/settings.js').then(()=>ok('settings','./core/settings.js')).catch(e=>fail('settings','./core/settings.js',e));
    // Wire Electron events to UI after core + ui modules are ready
    await import('./core/electron-bridge.js').then(()=>ok('electron-bridge','./core/electron-bridge.js')).catch(e=>fail('electron-bridge','./core/electron-bridge.js',e));

    await import('./index.js').then(()=>ok('app-shell','./index.js')).catch(e=>fail('app-shell','./index.js',e));

    // Falls App nicht auto-startet:
    if (window.App?.setupApplication) {
      await window.App.setupApplication();
    } else if (window.Backend?.init) {
      await window.Backend.init();
      console.log('[BOOT] Backend.initialize() fallback done');
    }

    console.log('[BOOT] main.js initialized (all modules loaded)');
  } catch (e) {
    console.error('[BOOT] Fehler beim Module-Bootstrap:', e);
  }
})();
