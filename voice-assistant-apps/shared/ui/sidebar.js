// ui/sidebar.js
import { SidebarCore }   from './sidebar-core.js';
import { SidebarTabs }   from './sidebar-tabs.js';
import { SidebarEvents } from './sidebar-events.js';
import { SidebarTheme }  from './sidebar-theme.js';


export const sidebarManager = {
  async initialize() {
    if (SidebarCore.state.initialized) return;
    SidebarCore.queryDom();
    SidebarCore.ensureDom();
    SidebarEvents.bind();
    SidebarTabs.initFromHash();
    SidebarTheme.init();
    SidebarCore.state.initialized = true;
    console.log('[Sidebar] initialized');
  },
  switchTab(name) {
    SidebarTabs.switchTab(name);
  },
  isOpen() {
    return !!SidebarCore.state.open;
  },
  open() {
    SidebarCore.state.open = true;
    document.body.classList.add('sidebar-open');
  },
  close() {
    SidebarCore.state.open = false;
    document.body.classList.remove('sidebar-open');
  }
};

// Optional global hook (falls index.js darauf zugreift)
window.sidebarManager = window.sidebarManager || sidebarManager;
