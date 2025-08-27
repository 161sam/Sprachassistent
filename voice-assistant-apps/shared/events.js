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

  show(message, type = 'info', timeout = 5000) {
    if (!this.container) this.init();

    const note = DOMHelpers.createElement('div', { className: `notification ${type}` });
    const msg  = DOMHelpers.createElement('span', { className: 'message' }, message);
    const btn  = DOMHelpers.createElement('button', { className: 'close-btn', type: 'button' }, '×');

    // Statt onclick-Attribut → CSP-konformer EventListener
    btn.addEventListener('click', () => this.close(note));

    note.appendChild(msg);
    note.appendChild(btn);
    this.container.appendChild(note);

    if (timeout > 0) {
      setTimeout(() => this.close(note), timeout);
    }
  },

  close(note) {
    if (note && note.parentNode === this.container) {
      this.container.removeChild(note);
    }
  }
};

// Init beim DOMReady
DOMHelpers.ready(() => NotificationManager.init());
