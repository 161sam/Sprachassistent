// events.js
import { DOMHelpers } from './core/dom-helpers.js';

export const EventBus = {
  events: {},
  on(event, handler) {
    if (!this.events[event]) this.events[event] = [];
    this.events[event].push(handler);
  },
  off(event, handler) {
    if (!this.events[event]) return;
    this.events[event] = this.events[event].filter(h => h !== handler);
  },
  emit(event, data) {
    if (!this.events[event]) return;
    this.events[event].forEach(handler => handler(data));
  }
};

/**
 * Notification Manager – CSP-safe
 */
export const NotificationManager = {
  container: null,

  init() {
    this.container = DOMHelpers.get('#notificationContainer');
    if (!this.container) {
      this.container = DOMHelpers.createElement('div', { id: 'notificationContainer', className: 'notification-container' });
      document.body.appendChild(this.container);
    }
  },

  // Unified show(): supports two signatures
  // 1) show(message, type='info', timeout=5000)
  // 2) show(type, title, message, duration=4000)
  show(a, b, c, d) {
    if (!this.container) this.init();

    let type = 'info';
    let title = '';
    let message = '';
    let duration = 4000;

    const isVariantB = typeof a === 'string' && ['success','error','warning','info'].includes(a) && typeof b === 'string' && typeof c === 'string';
    if (isVariantB) {
      type = a || 'info';
      title = b || '';
      message = c || '';
      duration = typeof d === 'number' ? d : 4000;
    } else {
      message = a || '';
      type = typeof b === 'string' ? (b || 'info') : 'info';
      duration = typeof c === 'number' ? c : 5000;
    }

    const note = DOMHelpers.createElement('div', { className: `notification ${type}` });
    const content = DOMHelpers.createElement('div', { className: 'notification-content' });
    if (title) content.appendChild(DOMHelpers.createElement('div', { className: 'notification-title' }, title));
    content.appendChild(DOMHelpers.createElement('div', { className: 'notification-message' }, message));
    const btn  = DOMHelpers.createElement('button', { className: 'close-btn', type: 'button', 'aria-label': 'Schließen' }, '×');
    btn.addEventListener('click', () => this.close(note));

    note.appendChild(content);
    note.appendChild(btn);
    this.container.appendChild(note);

    if (duration > 0) setTimeout(() => this.close(note), duration);
  },

  close(note) {
    if (note && note.parentNode === this.container) {
      this.container.removeChild(note);
    }
  }
};

// Init beim DOMReady
DOMHelpers.ready(() => NotificationManager.init());
