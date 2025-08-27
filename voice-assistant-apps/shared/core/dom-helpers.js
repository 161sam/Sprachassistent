/**
 * DOM Helpers - Zentrale DOM Utilities
 * Stellt $ und $$ genau einmal zur Verfügung (guarded) und bietet
 * zusätzlich get()/all() als Methoden für modulare Importe.
 */

// Base selector functions
function querySelector(selector, context) {
  try {
    const root = context || document;
    return root.querySelector(selector);
  } catch (e) {
    console.warn('DOM selector error:', selector, e);
    return null;
  }
}

function querySelectorAll(selector, context) {
  try {
    const root = context || document;
    return root.querySelectorAll(selector);
  } catch (e) {
    console.warn('DOM selector error:', selector, e);
    return document.createDocumentFragment().childNodes; // leere NodeList
  }
}

// Guard: Nur einmalige Definition von $ und $$
if (typeof window.$ === 'undefined') {
  window.$ = querySelector;
}
if (typeof window.$$ === 'undefined') {
  window.$$ = querySelectorAll;
}

/**
 * DOM Utilities Objekt mit $ und $$ Integration
 * + Komfort-Methoden get()/all() für modulare Nutzung
 */
export const DOMHelpers = {
  // Direkte Referenzen
  $: querySelector,
  $$: querySelectorAll,

  // Neue, sprechende Aliase für modulare Aufrufer (z. B. Sidebar)
  get(selector, context) { return querySelector(selector, context); },
  all(selector, context) {
    // forEach-Sicherheit: in manchen Umgebungen hat NodeList kein forEach
    const list = querySelectorAll(selector, context);
    return typeof list.forEach === 'function' ? list : Array.from(list);
  },

  /** Wartet bis DOM bereit ist */
  ready(callback) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', callback);
    } else {
      callback();
    }
  },

  /** Erstellt Element mit Attributen und Inhalt */
  createElement(tag, attrs = {}, content = '') {
    const el = document.createElement(tag);
    Object.entries(attrs).forEach(([key, value]) => {
      if (key === 'className') el.className = value;
      else if (key === 'innerHTML') el.innerHTML = value;
      else if (key === 'textContent') el.textContent = value;
      else el.setAttribute(key, value);
    });
    if (content) {
      if (typeof content === 'string') el.textContent = content;
      else if (content instanceof Node) el.appendChild(content);
    }
    return el;
  },

  /** Toggle CSS Klasse mit Fallback */
  toggleClass(element, className, force) {
    const el = typeof element === 'string' ? this.$(element) : element;
    if (!el || !el.classList) return false;
    return typeof force !== 'undefined'
      ? el.classList.toggle(className, force)
      : el.classList.toggle(className);
  },

  /** Setzt Text mit Fallback */
  setText(element, text) {
    const el = typeof element === 'string' ? this.$(element) : element;
    if (el) el.textContent = text || '';
  },

  /** Setzt HTML mit Fallback */
  setHTML(element, html) {
    const el = typeof element === 'string' ? this.$(element) : element;
    if (el) el.innerHTML = html || '';
  },

  /** Event Listener mit Fallback hinzufügen */
  on(element, event, handler, options) {
    const el = typeof element === 'string' ? this.$(element) : element;
    if (el && typeof handler === 'function') {
      el.addEventListener(event, handler, options);
      return true;
    }
    return false;
  },

  /** Event Listener entfernen */
  off(element, event, handler) {
    const el = typeof element === 'string' ? this.$(element) : element;
    if (el && typeof handler === 'function') {
      el.removeEventListener(event, handler);
      return true;
    }
    return false;
  },

  /** CSS-Eigenschaft setzen */
  css(element, property, value) {
    const el = typeof element === 'string' ? this.$(element) : element;
    if (!el || !el.style) return;
    if (typeof property === 'object') {
      Object.entries(property).forEach(([prop, val]) => { el.style[prop] = val; });
    } else if (typeof property === 'string' && value !== undefined) {
      el.style[property] = value;
    }
  },

  /** Prüft ob Element sichtbar ist */
  isVisible(element) {
    const el = typeof element === 'string' ? this.$(element) : element;
    if (!el) return false;
    const style = window.getComputedStyle(el);
    return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
  },

  /** Smooth Scroll zu Element */
  scrollTo(element, options = {}) {
    const el = typeof element === 'string' ? this.$(element) : element;
    if (el && el.scrollIntoView) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start', inline: 'nearest', ...options });
    }
  },

  /** Debounce */
  debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction() {
      const context = this, args = arguments;
      const later = function() { timeout = null; if (!immediate) func.apply(context, args); };
      const callNow = immediate && !timeout;
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
      if (callNow) func.apply(context, args);
    };
  },

  /** Throttle */
  throttle(func, limit) {
    let inThrottle;
    return function() {
      const context = this, args = arguments;
      if (!inThrottle) {
        func.apply(context, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }
};
