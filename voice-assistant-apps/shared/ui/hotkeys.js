/**
 * Keyboard Shortcuts - Tastatur-Navigation
 * 
 * Zentrale Tastatur-Steuerung für den Sprachassistent
 * - Recording Controls (Space, R)
 * - Navigation (Tab, Escape)
 * - Settings & UI (F1, Ctrl+,)
 * - Accessibility Support
 */

import { DOMHelpers } from '../core/dom-helpers.js';

/**
 * Hotkey Configuration
 */
const HotkeyConfig = {
  // Recording Shortcuts
  recording: {
    toggle: ['Space', 'KeyR'],
    start: ['KeyF'],
    stop: ['Escape']
  },
  
  // Navigation
  navigation: {
    sidebar: ['KeyS', 'F1'],
    settings: ['Comma'], // Ctrl+,
    focus: ['KeyT'], // Focus text input
    avatar: ['KeyA'] // Avatar interaction
  },
  
  // UI Controls
  ui: {
    theme: ['KeyD'], // Toggle dark/light
    info: ['KeyI', 'F12'],
    reload: ['KeyR'], // Ctrl+R
    minimize: ['KeyM'] // Ctrl+M
  },
  
  // Modifier combinations
  modifiers: {
    ctrl: false,
    shift: false,
    alt: false,
    meta: false
  },
  
  // State
  enabled: true,
  recording: false
};

/**
 * Hotkey Manager Class
 */
class HotkeyManager {
  constructor() {
    this.shortcuts = new Map();
    this.modifierKeys = new Set(['Control', 'Shift', 'Alt', 'Meta']);
    this.preventDefaults = new Set(['Space', 'KeyR', 'KeyF']);
    this.globalShortcuts = new Set(['Escape', 'F1', 'F12']);
    this.setup();
  }

  /**
   * Initialize Hotkey System
   */
  setup() {
    // Register all shortcuts
    this.registerShortcuts();
    
    // Setup event listeners
    document.addEventListener('keydown', this.handleKeyDown.bind(this));
    document.addEventListener('keyup', this.handleKeyUp.bind(this));
    
    // Handle window focus for recording state
    window.addEventListener('blur', this.handleWindowBlur.bind(this));
    window.addEventListener('focus', this.handleWindowFocus.bind(this));
    
    console.log('Hotkey Manager initialized');
  }

  /**
   * Register all keyboard shortcuts
   */
  registerShortcuts() {
    // Recording Controls
    this.register(['Space'], this.toggleRecording.bind(this), 'Toggle Recording');
    this.register(['KeyR'], this.toggleRecording.bind(this), 'Toggle Recording (R)');
    this.register(['KeyF'], this.startRecording.bind(this), 'Start Recording');
    this.register(['Escape'], this.stopAction.bind(this), 'Stop/Cancel');
    
    // Navigation
    this.register(['KeyS'], this.toggleSidebar.bind(this), 'Toggle Sidebar');
    this.register(['F1'], this.toggleSidebar.bind(this), 'Help/Settings');
    this.register(['KeyT'], this.focusTextInput.bind(this), 'Focus Text Input');
    this.register(['KeyA'], this.clickAvatar.bind(this), 'Avatar Interaction');
    
    // UI Controls
    this.register(['KeyD'], this.toggleTheme.bind(this), 'Toggle Theme');
    this.register(['KeyI'], this.showInfo.bind(this), 'Show Info');
    this.register(['F12'], this.showInfo.bind(this), 'Show Info (F12)');
    
    // Modifier combinations
    this.register(['Comma'], this.openSettings.bind(this), 'Settings', ['ctrl']);
    this.register(['KeyR'], this.reloadApp.bind(this), 'Reload', ['ctrl']);
    this.register(['KeyM'], this.minimizeWindow.bind(this), 'Minimize', ['ctrl']);
    this.register(['Slash'], this.showShortcuts.bind(this), 'Show Shortcuts', ['ctrl']);
  }

  /**
   * Register a keyboard shortcut
   * @param {string[]} keys - Key combinations
   * @param {Function} callback - Function to call
   * @param {string} description - Description for help
   * @param {string[]} modifiers - Required modifiers
   */
  register(keys, callback, description = '', modifiers = []) {
    const shortcut = {
      keys: new Set(keys),
      callback,
      description,
      modifiers: new Set(modifiers),
      enabled: true
    };
    
    const keyId = keys.join('+') + (modifiers.length ? ':' + modifiers.join('+') : '');
    this.shortcuts.set(keyId, shortcut);
  }

  /**
   * Handle keydown events
   * @param {KeyboardEvent} event 
   */
  handleKeyDown(event) {
    if (!HotkeyConfig.enabled) return;
    
    // Update modifier state
    this.updateModifiers(event);
    
    // Skip if typing in input fields (unless global shortcut)
    if (this.isTypingContext(event) && !this.globalShortcuts.has(event.code)) {
      return;
    }
    
    // Find matching shortcut
    const shortcut = this.findMatchingShortcut(event);
    
    if (shortcut) {
      // Prevent default if needed
      if (this.shouldPreventDefault(event)) {
        event.preventDefault();
        event.stopPropagation();
      }
      
      try {
        shortcut.callback(event);
        this.logShortcut(shortcut.description || event.code);
      } catch (error) {
        console.error('Shortcut error:', error);
      }
    }
  }

  /**
   * Handle keyup events  
   * @param {KeyboardEvent} event 
   */
  handleKeyUp(event) {
    this.updateModifiers(event);
  }

  /**
   * Update modifier key state
   * @param {KeyboardEvent} event 
   */
  updateModifiers(event) {
    HotkeyConfig.modifiers.ctrl = event.ctrlKey;
    HotkeyConfig.modifiers.shift = event.shiftKey;
    HotkeyConfig.modifiers.alt = event.altKey;
    HotkeyConfig.modifiers.meta = event.metaKey;
  }

  /**
   * Find matching keyboard shortcut
   * @param {KeyboardEvent} event 
   * @returns {Object|null}
   */
  findMatchingShortcut(event) {
    for (const [keyId, shortcut] of this.shortcuts) {
      if (!shortcut.enabled) continue;
      
      // Check if key matches
      if (!shortcut.keys.has(event.code)) continue;
      
      // Check modifiers
      const modifiersMatch = this.checkModifiers(shortcut.modifiers);
      if (!modifiersMatch) continue;
      
      return shortcut;
    }
    return null;
  }

  /**
   * Check if required modifiers are pressed
   * @param {Set} requiredModifiers 
   * @returns {boolean}
   */
  checkModifiers(requiredModifiers) {
    const currentModifiers = HotkeyConfig.modifiers;
    
    // Check each required modifier
    for (const modifier of requiredModifiers) {
      if (!currentModifiers[modifier]) return false;
    }
    
    // Check no extra modifiers (unless explicitly allowed)
    const activeModifiers = Object.entries(currentModifiers)
      .filter(([_, active]) => active)
      .map(([key, _]) => key);
    
    return activeModifiers.length === requiredModifiers.size;
  }

  /**
   * Check if user is typing in an input context
   * @param {KeyboardEvent} event 
   * @returns {boolean}
   */
  isTypingContext(event) {
    const target = event.target;
    const tagName = target.tagName?.toLowerCase();
    const inputTypes = ['input', 'textarea', 'select'];
    const contentEditable = target.contentEditable === 'true';
    
    return inputTypes.includes(tagName) || contentEditable;
  }

  /**
   * Check if default should be prevented
   * @param {KeyboardEvent} event 
   * @returns {boolean}
   */
  shouldPreventDefault(event) {
    // Always prevent for recording keys
    if (this.preventDefaults.has(event.code)) return true;
    
    // Prevent for Ctrl combinations
    if (event.ctrlKey || event.metaKey) return true;
    
    // Prevent for function keys
    if (event.code.startsWith('F')) return true;
    
    return false;
  }

  /**
   * Window blur handler - pause recording
   */
  handleWindowBlur() {
    if (HotkeyConfig.recording) {
      this.stopRecording();
    }
  }

  /**
   * Window focus handler - resume if needed
   */
  handleWindowFocus() {
    // Resume functionality if needed
    console.log('Window focused - hotkeys active');
  }

  /**
   * Log shortcut usage
   * @param {string} description 
   */
  logShortcut(description) {
    console.log(`Shortcut: ${description}`);
  }

  // ================================================================
  // SHORTCUT ACTIONS
  // ================================================================

  /**
   * Toggle recording state
   */
  toggleRecording() {
    if (window.App && typeof window.App.toggleRecording === 'function') {
      window.App.toggleRecording();
    } else {
      console.warn('App.toggleRecording not available');
    }
  }

  /**
   * Start recording
   */
  startRecording() {
    if (window.App && typeof window.App.startRecording === 'function') {
      window.App.startRecording();
    } else {
      console.warn('App.startRecording not available');
    }
  }

  /**
   * Stop current action
   */
  stopAction() {
    if (HotkeyConfig.recording && window.App) {
      if (typeof window.App.stopRecording === 'function') {
        window.App.stopRecording();
      }
    } else {
      // Close sidebar or other UI elements
      this.closeSidebar();
    }
  }

  /**
   * Toggle sidebar
   */
  toggleSidebar() {
    if (window.App && typeof window.App.toggleSidebar === 'function') {
      window.App.toggleSidebar();
    }
  }

  /**
   * Close sidebar
   */
  closeSidebar() {
    if (window.App && typeof window.App.closeSidebar === 'function') {
      window.App.closeSidebar();
    }
  }

  /**
   * Focus text input
   */
  focusTextInput() {
    const textInput = DOMHelpers.$('#textInput') || DOMHelpers.$('input[type="text"]');
    if (textInput) {
      textInput.focus();
      textInput.select();
    }
  }

  /**
   * Click avatar interaction
   */
  clickAvatar() {
    if (window.App && typeof window.App.handleAvatarClick === 'function') {
      window.App.handleAvatarClick();
    } else {
      const avatar = DOMHelpers.$('#avatar, .avatar-container');
      if (avatar) {
        avatar.click();
      }
    }
  }

  /**
   * Toggle theme
   */
  toggleTheme() {
    if (window.App && typeof window.App.cycleTheme === 'function') {
      window.App.cycleTheme();
    }
  }

  /**
   * Show info dialog
   */
  showInfo() {
    if (window.App && typeof window.App.showInfo === 'function') {
      window.App.showInfo();
    }
  }

  /**
   * Open settings (Ctrl+,)
   */
  openSettings() {
    this.toggleSidebar();
  }

  /**
   * Reload application (Ctrl+R)
   */
  reloadApp() {
    if (window.electronAPI) {
      // Electron app reload
      window.location.reload();
    } else {
      window.location.reload();
    }
  }

  /**
   * Minimize window (Ctrl+M)
   */
  minimizeWindow() {
    if (window.electronAPI && typeof window.electronAPI.minimize === 'function') {
      window.electronAPI.minimize();
    }
  }

  /**
   * Show available shortcuts
   */
  showShortcuts() {
    const shortcuts = Array.from(this.shortcuts.entries())
      .map(([key, shortcut]) => `${key}: ${shortcut.description}`)
      .join('\n');
    
    console.log('Available Shortcuts:\n' + shortcuts);
    
    // Show in UI if possible
    if (window.App && typeof window.App.showNotification === 'function') {
      window.App.showNotification('info', 'Keyboard Shortcuts', 'Check console for full list');
    }
  }

  // ================================================================
  // PUBLIC API
  // ================================================================

  /**
   * Enable/disable hotkeys
   * @param {boolean} enabled 
   */
  setEnabled(enabled) {
    HotkeyConfig.enabled = enabled;
    console.log(`Hotkeys ${enabled ? 'enabled' : 'disabled'}`);
  }

  /**
   * Get current shortcuts
   * @returns {Map}
   */
  getShortcuts() {
    return new Map(this.shortcuts);
  }

  /**
   * Enable/disable specific shortcut
   * @param {string} keyId 
   * @param {boolean} enabled 
   */
  setShortcutEnabled(keyId, enabled) {
    if (this.shortcuts.has(keyId)) {
      this.shortcuts.get(keyId).enabled = enabled;
    }
  }

  /**
   * Cleanup event listeners
   */
  destroy() {
    document.removeEventListener('keydown', this.handleKeyDown.bind(this));
    document.removeEventListener('keyup', this.handleKeyUp.bind(this));
    window.removeEventListener('blur', this.handleWindowBlur.bind(this));
    window.removeEventListener('focus', this.handleWindowFocus.bind(this));
    this.shortcuts.clear();
  }
}

// Initialize and export
const hotkeyManager = new HotkeyManager();

export default hotkeyManager;
export { HotkeyConfig, HotkeyManager };
