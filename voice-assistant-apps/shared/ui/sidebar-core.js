// ui/sidebar-core.js
import { DOMHelpers } from '../core/dom-helpers.js';

export const SidebarCore = {
  els: {
    root: null,
    navItems: [],
    panels: [],
    toggleBtn: null,
  },
  state: {
    open: false,
    activeTab: 'llm', // default
    initialized: false,
  },
  queryDom() {
    this.els.root      = DOMHelpers.get('#sidebar');
    this.els.toggleBtn = DOMHelpers.get('#sidebarToggle');
    this.els.navItems  = DOMHelpers.all('.sidebar-nav-item');
    this.els.panels    = DOMHelpers.all('.sidebar-panel');
  },
  ensureDom() {
    if (!this.els.root)      throw new Error('Sidebar root #sidebar missing');
    if (!this.els.toggleBtn) throw new Error('Sidebar toggle #sidebarToggle missing');
  }
};
