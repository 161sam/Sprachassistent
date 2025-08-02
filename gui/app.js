/**
 * Enhanced Voice Assistant GUI with Optimized Audio Streaming
 * Features:
 * - Real-time audio streaming with minimal latency
 * - Enhanced UI with performance monitoring
 * - Mobile-optimized interface
 * - Advanced settings management
 */

// Import the optimized components
// Note: These will be loaded via script tags in the HTML
// OptimizedAudioStreamer and EnhancedVoiceAssistant are globally available

class VoiceAssistantGUI {
    constructor() {
        this.voiceAssistant = null;
        this.isRecording = false;
        this.recordingTimer = null;
        this.recordingStartTime = null;
        
        // Enhanced settings with new streaming options
        this.settings = {
            // Audio streaming settings
            audioStreaming: true,
            realTimeTranscription: false,
            chunkSize: 1024,
            chunkIntervalMs: 50,
            adaptiveQuality: true,
            
            // Original settings
            responseNebel: true,
            avatarAnimation: true,
            animationSpeed: 1.0,
            nebelColors: {
                primary: '#6366f1',
                secondary: '#10b981', 
                accent: '#f59e0b'
            },
            autoStopTime: 30000,
            noiseSuppression: true,
            echoCancellation: true,
            notifications: true,
            reducedMotion: false,
            glassOpacity: 0.05,
            autoReconnect: true,
            connectionTimeout: 3000,
            debugMode: false,
            
            // Performance monitoring
            showPerformanceMetrics: false,
            enableLatencyMonitoring: true
        };
        
        this.performanceMetrics = {
            latency: [],
            audioChunks: 0,
            reconnections: 0,
            errors: 0
        };
    }

    async initialize() {
        console.log('🚀 Initializing Enhanced Voice Assistant GUI...');
        
        try {
            // Initialize the optimized voice assistant
            const config = {
                wsUrl: this.getWebSocketURL(),
                chunkSize: this.settings.chunkSize,
                chunkIntervalMs: this.settings.chunkIntervalMs,
                adaptiveQuality: this.settings.adaptiveQuality,
                enableMetrics: this.settings.enableLatencyMonitoring
            };
            
            this.voiceAssistant = new EnhancedVoiceAssistant(config);
            
            // Set up UI elements
            this.voiceAssistant.ui = {
                statusElement: document.getElementById('statusText'),
                responseElement: document.getElementById('response'),
                recordButton: document.getElementById('voiceBtn'),
                metricsElement: document.getElementById('performanceMetrics')
            };
            
            // Initialize the voice assistant
            const success = await this.voiceAssistant.initialize();
            
            if (success) {
                console.log('✅ Enhanced Voice Assistant initialized successfully');
                this.showNotification('success', 'System Ready', 'Voice Assistant optimized and ready');
                this.updateStatus('connected', '✅ Verbunden mit optimiertem Server');
                
                // Start performance monitoring if enabled
                if (this.settings.showPerformanceMetrics) {
                    this.startPerformanceMonitoring();
                }
            } else {
                throw new Error('Failed to initialize voice assistant');
            }
            
            // Set up event listeners
            this.setupEventListeners();
            
            // Apply settings
            this.applySettings();
            
        } catch (error) {
            console.error('❌ GUI initialization failed:', error);
            this.showNotification('error', 'Initialization Failed', error.message);
            this.updateStatus('error', '❌ Verbindungsfehler');
        }
    }

    setupEventListeners() {
        // Text input handling
        const textInput = document.getElementById('textInput');
        if (textInput) {
            textInput.addEventListener('keypress', (event) => {
                if (event.key === 'Enter') {
                    this.sendText();
                }
            });
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            // Ctrl/Cmd + Enter for voice input
            if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
                event.preventDefault();
                this.toggleRecording();
            }
            
            // Ctrl/Cmd + , for settings
            if ((event.ctrlKey || event.metaKey) && event.key === ',') {
                event.preventDefault();
                this.openSettingsModal();
            }
            
            // ESC to stop recording or close menus
            if (event.key === 'Escape') {
                if (this.isRecording) {
                    this.stopRecording();
                } else {
                    this.closeAllMenus();
                }
            }
            
            // F12 to toggle performance metrics
            if (event.key === 'F12') {
                event.preventDefault();
                this.togglePerformanceMetrics();
            }
        });

        // Click outside to close menus
        document.addEventListener('click', (event) => {
            this.handleOutsideClick(event);
        });
    }

    async toggleRecording() {
        if (this.isRecording) {
            await this.stopRecording();
        } else {
            await this.startRecording();
        }
    }

    async startRecording() {
        if (this.isRecording || !this.voiceAssistant) return;

        try {
            const success = await this.voiceAssistant.startRecording();
            
            if (success) {
                this.isRecording = true;
                this.recordingStartTime = Date.now();
                this.updateRecordingUI(true);
                this.startRecordingTimer();
                
                // Show nebel animation
                this.showNebelAnimation();
                
                // Auto-stop after configured time
                setTimeout(() => {
                    if (this.isRecording) {
                        this.stopRecording();
                    }
                }, this.settings.autoStopTime);
                
                if (this.settings.notifications) {
                    this.showNotification('success', 'Aufnahme gestartet', 'Sprechen Sie jetzt...');
                }
            } else {
                throw new Error('Failed to start recording');
            }
            
        } catch (error) {
            console.error('Recording start failed:', error);
            this.showNotification('error', 'Aufnahme fehlgeschlagen', error.message);
            this.performanceMetrics.errors++;
        }
    }

    async stopRecording() {
        if (!this.isRecording || !this.voiceAssistant) return;

        try {
            await this.voiceAssistant.stopRecording();
            
            this.isRecording = false;
            this.recordingStartTime = null;
            this.updateRecordingUI(false);
            this.stopRecordingTimer();
            
            if (this.settings.notifications) {
                this.showNotification('success', 'Aufnahme beendet', 'Wird verarbeitet...');
            }
            
        } catch (error) {
            console.error('Recording stop failed:', error);
            this.showNotification('error', 'Fehler beim Stoppen', error.message);
            this.performanceMetrics.errors++;
        }
    }

    async sendText() {
        const textInput = document.getElementById('textInput');
        const sendBtn = document.getElementById('sendBtn');
        
        if (!textInput || !textInput.value.trim()) return;
        
        try {
            sendBtn.classList.add('loading');
            sendBtn.disabled = true;
            
            this.showNebelAnimation();
            this.displayResponse("Verarbeite Ihre Anfrage...");
            
            const success = await this.voiceAssistant.sendText(textInput.value.trim());
            
            if (success) {
                textInput.value = '';
            } else {
                throw new Error('Failed to send message');
            }
            
        } catch (error) {
            console.error('Text sending failed:', error);
            this.showNotification('error', 'Nachricht fehlgeschlagen', error.message);
            this.hideNebelAnimation();
        } finally {
            setTimeout(() => {
                sendBtn.classList.remove('loading');
                sendBtn.disabled = false;
            }, 1000);
        }
    }

    startPerformanceMonitoring() {
        const metricsContainer = this.createPerformanceMetricsUI();
        
        setInterval(() => {
            if (this.voiceAssistant && this.settings.showPerformanceMetrics) {
                const metrics = this.voiceAssistant.getMetrics();
                this.updatePerformanceMetricsDisplay(metrics);
            }
        }, 1000);
    }

    createPerformanceMetricsUI() {
        let container = document.getElementById('performanceMetrics');
        
        if (!container) {
            container = document.createElement('div');
            container.id = 'performanceMetrics';
            container.className = 'performance-metrics';
            container.style.cssText = `
                position: fixed;
                top: 80px;
                left: 20px;
                background: rgba(0,0,0,0.8);
                color: white;
                padding: 10px;
                border-radius: 8px;
                font-family: monospace;
                font-size: 12px;
                z-index: 1000;
                min-width: 200px;
                display: none;
            `;
            
            container.innerHTML = `
                <div><strong>📊 Performance Metrics</strong></div>
                <div>Status: <span id="perfStatus">-</span></div>
                <div>Latency: <span id="perfLatency">-</span>ms (avg)</div>
                <div>Audio Chunks: <span id="perfChunks">-</span></div>
                <div>Data Transfer: <span id="perfBytes">-</span></div>
                <div>Reconnections: <span id="perfReconnects">-</span></div>
                <div>Errors: <span id="perfErrors">-</span></div>
            `;
            
            document.body.appendChild(container);
        }
        
        return container;
    }

    updatePerformanceMetricsDisplay(metrics) {
        const container = document.getElementById('performanceMetrics');
        if (!container) return;
        
        const elements = {
            perfStatus: metrics.connected ? 'Connected' : 'Disconnected',
            perfLatency: metrics.latency.average || 0,
            perfChunks: metrics.audio.chunksSent || 0,
            perfBytes: this.formatBytes(metrics.audio.totalBytes || 0),
            perfReconnects: metrics.connection.reconnections || 0,
            perfErrors: this.performanceMetrics.errors
        };
        
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
        
        // Update color based on latency
        const latencyElement = document.getElementById('perfLatency');
        if (latencyElement) {
            const latency = metrics.latency.average || 0;
            if (latency < 100) {
                latencyElement.style.color = '#10b981'; // green
            } else if (latency < 300) {
                latencyElement.style.color = '#f59e0b'; // yellow
            } else {
                latencyElement.style.color = '#ef4444'; // red
            }
        }
    }

    togglePerformanceMetrics() {
        this.settings.showPerformanceMetrics = !this.settings.showPerformanceMetrics;
        const container = document.getElementById('performanceMetrics');
        
        if (container) {
            container.style.display = this.settings.showPerformanceMetrics ? 'block' : 'none';
        }
        
        if (this.settings.showPerformanceMetrics && !container) {
            this.startPerformanceMonitoring();
        }
        
        this.showNotification('success', 'Performance Metrics', 
            this.settings.showPerformanceMetrics ? 'Aktiviert (F12 zum Ausblenden)' : 'Deaktiviert');
    }

    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    // UI Update methods
    updateRecordingUI(recording) {
        const voiceBtn = document.getElementById('voiceBtn');
        const voiceIcon = document.getElementById('voiceIcon');
        const indicator = document.getElementById('recordingIndicator');
        
        if (recording) {
            voiceBtn.classList.add('recording');
            voiceIcon.textContent = '⏹️';
            indicator.classList.add('active');
        } else {
            voiceBtn.classList.remove('recording');
            voiceIcon.textContent = '🎙️';
            indicator.classList.remove('active');
        }
    }

    startRecordingTimer() {
        this.recordingTimer = setInterval(() => {
            if (this.recordingStartTime) {
                const elapsed = Math.floor((Date.now() - this.recordingStartTime) / 1000);
                const timeElement = document.getElementById('recordingTime');
                if (timeElement) {
                    timeElement.textContent = `${elapsed}s`;
                }
            }
        }, 100);
    }

    stopRecordingTimer() {
        if (this.recordingTimer) {
            clearInterval(this.recordingTimer);
            this.recordingTimer = null;
        }
    }

    updateStatus(type, message) {
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        
        if (statusDot) {
            statusDot.className = `status-dot ${type}`;
        }
        
        if (statusText) {
            statusText.textContent = message;
        }
    }

    showNebelAnimation() {
        if (this.settings.responseNebel) {
            this.activateAvatar();
            const nebelElement = document.getElementById('nebelAnimation');
            const responseElement = document.getElementById('response');
            
            if (nebelElement) {
                nebelElement.classList.add('active');
            }
            
            if (responseElement) {
                responseElement.style.opacity = '0.3';
            }
        }
    }

    hideNebelAnimation() {
        this.deactivateAvatar();
        const nebelElement = document.getElementById('nebelAnimation');
        const responseElement = document.getElementById('response');
        
        if (nebelElement) {
            nebelElement.classList.remove('active');
        }
        
        if (responseElement) {
            responseElement.style.opacity = '1';
        }
    }

    activateAvatar() {
        const avatar = document.getElementById('avatar');
        if (avatar) {
            avatar.classList.add('active');
        }
    }

    deactivateAvatar() {
        const avatar = document.getElementById('avatar');
        if (avatar) {
            avatar.classList.remove('active');
        }
    }

    displayResponse(content) {
        const responseElement = document.getElementById('response');
        if (!responseElement) return;
        
        responseElement.innerHTML = '<div class="response-content"></div>';
        const container = responseElement.firstElementChild;
        
        this.matrixRain(container, content);
        
        // Smooth scroll to response
        responseElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    matrixRain(element, text) {
        const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789゠ァアィイゥウ';
        let iteration = 0;
        
        const interval = setInterval(() => {
            element.textContent = text
                .split('')
                .map((char, index) => {
                    if (index < iteration) {
                        return char;
                    }
                    return letters[Math.floor(Math.random() * letters.length)];
                })
                .join('');
                
            if (iteration >= text.length) {
                clearInterval(interval);
                element.textContent = text;
            }
            iteration += 1;
        }, 50);
    }

    clearResponse() {
        const responseElement = document.getElementById('response');
        if (responseElement) {
            responseElement.innerHTML = '<div class="response-empty">Ihre Antwort erscheint hier...</div>';
        }
        
        this.hideNebelAnimation();
        
        if (this.settings.notifications) {
            this.showNotification('success', 'Gelöscht', 'Antwort wurde gelöscht');
        }
    }

    // Notification System
    showNotification(type, title, message, duration = 5000) {
        if (!this.settings.notifications) return;
        
        const container = document.getElementById('notificationContainer');
        if (!container) return;
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div class="notification-icon">
                ${type === 'success' ? '✅' : type === 'error' ? '❌' : '⚠️'}
            </div>
            <div class="notification-content">
                <div class="notification-title">${title}</div>
                <div class="notification-message">${message}</div>
            </div>
            <button class="notification-close" onclick="this.closest('.notification').remove()">×</button>
        `;
        
        container.appendChild(notification);
        
        // Animate in
        setTimeout(() => notification.classList.add('show'), 100);
        
        // Auto remove
        setTimeout(() => {
            if (notification.parentNode) {
                notification.classList.remove('show');
                setTimeout(() => notification.remove(), 300);
            }
        }, duration);
    }

    // Settings Management
    applySettings() {
        this.applyAnimationSpeed();
        this.applyNebelColors();
        this.applyGlassOpacity();
        this.applyReducedMotion();
        
        // Update voice assistant config if available
        if (this.voiceAssistant && this.voiceAssistant.streamer) {
            const streamer = this.voiceAssistant.streamer;
            streamer.config.chunkSize = this.settings.chunkSize;
            streamer.config.chunkIntervalMs = this.settings.chunkIntervalMs;
            streamer.config.adaptiveQuality = this.settings.adaptiveQuality;
        }
    }

    applyAnimationSpeed() {
        const speed = this.settings.animationSpeed;
        document.documentElement.style.setProperty('--animation-speed', `${4/speed}s`);
        document.documentElement.style.setProperty('--avatar-speed', `${4/speed}s`);
        document.documentElement.style.setProperty('--nebel-speed', `${3/speed}s`);
    }

    applyNebelColors() {
        const colors = this.settings.nebelColors;
        document.documentElement.style.setProperty('--nebel-primary', colors.primary);
        document.documentElement.style.setProperty('--nebel-secondary', colors.secondary);
        document.documentElement.style.setProperty('--nebel-accent', colors.accent);
    }

    applyGlassOpacity() {
        document.documentElement.style.setProperty('--glass-bg', `rgba(255, 255, 255, ${this.settings.glassOpacity})`);
    }

    applyReducedMotion() {
        if (this.settings.reducedMotion) {
            document.body.classList.add('reduced-motion');
        } else {
            document.body.classList.remove('reduced-motion');
        }
    }

    // Utility methods
    getWebSocketURL() {
        const hostname = window.location.hostname;
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        
        // Try different possible URLs
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return 'ws://localhost:8123';
        }
        
        // For Raspberry Pi setups
        const possibleHosts = [
            `${protocol}//${hostname}:8123`,
            `ws://raspi4.local:8123`,
            `ws://raspi4.headscale:8123`,
            `ws://${hostname}:8123`
        ];
        
        return possibleHosts[0]; // The streamer will handle fallbacks
    }

    handleOutsideClick(event) {
        const settingsBtn = document.getElementById('settingsBtn');
        const settingsMenu = document.getElementById('settingsMenu');
        const settingsModal = document.getElementById('settingsModal');
        
        if (settingsBtn && settingsMenu && !settingsBtn.contains(event.target)) {
            settingsMenu.classList.remove('active');
        }
        
        if (settingsModal && event.target === settingsModal) {
            settingsModal.classList.remove('active');
        }
    }

    closeAllMenus() {
        const settingsMenu = document.getElementById('settingsMenu');
        const settingsModal = document.getElementById('settingsModal');
        
        if (settingsMenu) {
            settingsMenu.classList.remove('active');
        }
        
        if (settingsModal) {
            settingsModal.classList.remove('active');
        }
    }

    // Settings Modal Functions
    openSettingsModal() {
        const modal = document.getElementById('settingsModal');
        if (modal) {
            modal.classList.add('active');
            this.loadSettingsUI();
        }
    }

    closeSettingsModal() {
        const modal = document.getElementById('settingsModal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    loadSettingsUI() {
        // Load current settings into UI elements
        // This function would update all the UI controls to reflect current settings
        const elements = [
            ['responseNebelToggle', 'responseNebel'],
            ['avatarAnimationToggle', 'avatarAnimation'],
            ['noiseSuppression', 'noiseSuppression'],
            ['echoCancellation', 'echoCancellation'],
            ['notificationsToggle', 'notifications'],
            ['reducedMotion', 'reducedMotion'],
            ['autoReconnect', 'autoReconnect'],
            ['debugMode', 'debugMode']
        ];
        
        elements.forEach(([elementId, settingName]) => {
            const element = document.getElementById(elementId);
            if (element) {
                element.classList.toggle('active', this.settings[settingName]);
            }
        });
        
        // Update sliders and selects
        const animationSpeedSlider = document.getElementById('animationSpeedSlider');
        const speedValue = document.getElementById('speedValue');
        if (animationSpeedSlider && speedValue) {
            animationSpeedSlider.value = this.settings.animationSpeed;
            speedValue.textContent = this.settings.animationSpeed.toFixed(1) + 'x';
        }
        
        const glassOpacitySlider = document.getElementById('glassOpacitySlider');
        const glassValue = document.getElementById('glassValue');
        if (glassOpacitySlider && glassValue) {
            glassOpacitySlider.value = this.settings.glassOpacity;
            glassValue.textContent = Math.round(this.settings.glassOpacity * 100) + '%';
        }
    }

    toggleSetting(settingName) {
        this.settings[settingName] = !this.settings[settingName];
        
        // Update UI
        const toggle = document.getElementById(`${settingName}Toggle`) || document.getElementById(settingName);
        if (toggle) {
            toggle.classList.toggle('active', this.settings[settingName]);
        }
        
        // Apply setting immediately
        this.applySettings();
        
        if (this.settings.notifications) {
            this.showNotification('success', 'Einstellung geändert', 
                `${settingName} wurde ${this.settings[settingName] ? 'aktiviert' : 'deaktiviert'}`);
        }
    }

    updateAnimationSpeed(value) {
        this.settings.animationSpeed = parseFloat(value);
        const speedValue = document.getElementById('speedValue');
        if (speedValue) {
            speedValue.textContent = value + 'x';
        }
        this.applyAnimationSpeed();
    }

    updateGlassOpacity(value) {
        this.settings.glassOpacity = parseFloat(value);
        const glassValue = document.getElementById('glassValue');
        if (glassValue) {
            glassValue.textContent = Math.round(value * 100) + '%';
        }
        this.applyGlassOpacity();
    }

    setNebelColor(type, color) {
        this.settings.nebelColors[type] = color;
        this.applyNebelColors();
        
        if (this.settings.notifications) {
            this.showNotification('success', 'Farbe geändert', `${type} Farbe wurde aktualisiert`);
        }
    }
}

// Global instance
let voiceAssistantGUI = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async function() {
    console.log('🎨 Initializing Enhanced Voice Assistant GUI...');
    
    voiceAssistantGUI = new VoiceAssistantGUI();
    await voiceAssistantGUI.initialize();
    
    // Focus on text input
    const textInput = document.getElementById('textInput');
    if (textInput) {
        textInput.focus();
    }
});

// Make functions globally available for HTML onclick handlers
window.toggleRecording = () => voiceAssistantGUI?.toggleRecording();
window.sendText = () => voiceAssistantGUI?.sendText();
window.clearResponse = () => voiceAssistantGUI?.clearResponse();
window.openSettingsModal = () => voiceAssistantGUI?.openSettingsModal();
window.closeSettingsModal = () => voiceAssistantGUI?.closeSettingsModal();
window.toggleSetting = (setting) => voiceAssistantGUI?.toggleSetting(setting);
window.updateAnimationSpeed = (value) => voiceAssistantGUI?.updateAnimationSpeed(value);
window.updateGlassOpacity = (value) => voiceAssistantGUI?.updateGlassOpacity(value);
window.setNebelColor = (type, color) => voiceAssistantGUI?.setNebelColor(type, color);

// Settings menu functions
window.toggleSettingsMenu = () => {
    const menu = document.getElementById('settingsMenu');
    if (menu) {
        menu.classList.toggle('active');
    }
};

window.openSettingsTab = (tabName) => {
    const menu = document.getElementById('settingsMenu');
    if (menu) {
        menu.classList.remove('active');
    }
    voiceAssistantGUI?.openSettingsModal();
    
    setTimeout(() => {
        const tab = document.querySelector(`[data-tab="${tabName}"]`);
        if (tab) {
            tab.click();
        }
    }, 100);
};

window.switchTab = (tabName) => {
    // Remove active from all tabs and panels
    document.querySelectorAll('.settings-tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.settings-panel').forEach(panel => panel.classList.remove('active'));
    
    // Activate selected tab and panel
    const targetTab = document.querySelector(`[data-tab="${tabName}"]`);
    const panel = document.getElementById(`panel-${tabName}`);
    
    if (targetTab) targetTab.classList.add('active');
    if (panel) panel.classList.add('active');
};

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceAssistantGUI;
}
