// ui/sidebar.js – unified imports without aliases
import { SidebarCore } from './sidebar-core.js';
import { SidebarTabs } from './sidebar-tabs.js';
import { SidebarEvents } from './sidebar-events.js';
import * as SidebarTheme from './sidebar-theme.js';

export const sidebarManager = {
  async initialize() {
    if (SidebarCore.state.initialized) return;
    SidebarCore.queryDom();
    SidebarCore.ensureDom();
    SidebarEvents.bind();
    SidebarTheme.init();
    SidebarCore.state.initialized = true;
    console.log('[Sidebar] initialized');
  },
  switchTab(name) {
    const btn = document.querySelector(`.sidebar-nav-item[data-tab="${name}"]`);
    if (btn) btn.click();
  },
  isOpen() {
    return !!SidebarCore.state.open;
  },
  open() {
    SidebarCore.state.open = true;
    document.body.classList.add('sidebar-open');
    const root = SidebarCore.els.root || document.getElementById('sidebar');
    if (root) root.classList.add('open');
  },
  close() {
    SidebarCore.state.open = false;
    document.body.classList.remove('sidebar-open');
    const root = SidebarCore.els.root || document.getElementById('sidebar');
    if (root) root.classList.remove('open');
  }
};

window.sidebarManager = window.sidebarManager || sidebarManager;
