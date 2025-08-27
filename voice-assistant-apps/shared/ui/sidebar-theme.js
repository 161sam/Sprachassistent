// Theme helpers with named exports only
import { DOMHelpers } from '../core/dom-helpers.js';

const STORAGE_KEY = 'va_theme';

export function init() {
  const saved = get();
  if (saved) apply(saved);
  DOMHelpers.all('.theme-card').forEach(card => {
    card.addEventListener('click', () => apply(card.dataset.theme));
  });
}

export function apply(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  try { localStorage.setItem(STORAGE_KEY, theme); } catch {}
}

export function toggle() {
  const current = get() || document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'light' ? 'dark' : 'light';
  apply(next);
  return next;
}

export function get() {
  try { return localStorage.getItem(STORAGE_KEY); } catch { return null; }
}
