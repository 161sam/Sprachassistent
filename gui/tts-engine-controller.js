/**
 * TTS Engine Control Panel
 * Ermöglicht Echtzeitwechsel zwischen Piper und Kokoro TTS
 */

class TTSEngineController {
    constructor(voiceAssistant) {
        this.voiceAssistant = voiceAssistant;
        this.currentEngine = 'piper';
        this.currentVoice = null;
        this.availableEngines = [];
        this.availableVoices = {};
        this.isInitialized = false;
        
        this.createUI();
        this.setupEventListeners();
    }
    
    createUI() {
        // TTS Control Panel erstellen
        const controlPanel = document.createElement('div');
        controlPanel.id = 'tts-control-panel';
        controlPanel.className = 'tts-control-panel';
        controlPanel.innerHTML = `
            <div class="tts-panel-header">
                <h3>🎤 TTS Engine</h3>
                <div class="tts-status">
                    <span id="tts-current-engine" class="engine-badge">...</span>
                    <span id="tts-connection-status" class="status-indicator offline">●</span>
                </div>
            </div>
            
            <div class="tts-controls">
                <div class="engine-selector">
                    <label for="engine-select">Engine:</label>
                    <select id="engine-select" disabled>
                        <option value="">Lädt...</option>
                    </select>
                    <button id="switch-engine-btn" class="btn-switch" disabled>Wechseln</button>
                </div>
                
                <div class="voice-selector">
                    <label for="voice-select">Stimme:</label>
                    <select id="voice-select" disabled>
                        <option value="">Wähle Engine...</option>
                    </select>
                    <button id="set-voice-btn" class="btn-voice" disabled>Setzen</button>
                </div>
                
                <div class="tts-actions">
                    <button id="test-tts-btn" class="btn-test" disabled>🔊 Test</button>
                    <button id="test-all-engines-btn" class="btn-test-all" disabled>🔍 Alle testen</button>
                    <button id="refresh-tts-btn" class="btn-refresh" disabled>🔄 Aktualisieren</button>
                </div>
            </div>
            
            <div class="tts-info">
                <div class="engine-stats" id="engine-stats">
                    <p>Keine Engine-Informationen verfügbar</p>
                </div>
            </div>
        `;
        
        // CSS für TTS Control Panel
        const style = document.createElement('style');
        style.textContent = `
            .tts-control-panel {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                border-radius: 12px;
                padding: 16px;
                margin: 10px 0;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                color: white;
                font-family: 'Segoe UI', sans-serif;
            }
            
            .tts-panel-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 16px;
                padding-bottom: 12px;
                border-bottom: 1px solid rgba(255,255,255,0.2);
            }
            
            .tts-panel-header h3 {
                margin: 0;
                font-size: 18px;
                font-weight: 600;
            }
            
            .tts-status {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .engine-badge {
                background: rgba(255,255,255,0.2);
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .status-indicator {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                display: inline-block;
            }
            
            .status-indicator.online { background: #4ade80; }
            .status-indicator.offline { background: #ef4444; }
            .status-indicator.switching { 
                background: #f59e0b; 
                animation: pulse 1s infinite;
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            
            .tts-controls {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            
            .engine-selector, .voice-selector {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .tts-controls label {
                min-width: 60px;
                font-size: 14px;
                font-weight: 500;
            }
            
            .tts-controls select {
                flex: 1;
                padding: 8px 12px;
                border: none;
                border-radius: 6px;
                background: rgba(255,255,255,0.1);
                color: white;
                font-size: 14px;
            }
            
            .tts-controls select:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            
            .tts-controls button {
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .btn-switch {
                background: #10b981;
                color: white;
            }
            
            .btn-switch:hover:not(:disabled) {
                background: #059669;
                transform: translateY(-1px);
            }
            
            .btn-voice {
                background: #3b82f6;
                color: white;
            }
            
            .btn-voice:hover:not(:disabled) {
                background: #2563eb;
                transform: translateY(-1px);
            }
            
            .tts-actions {
                display: flex;
                gap: 8px;
                margin-top: 8px;
            }
            
            .btn-test {
                background: #8b5cf6;
                color: white;
                flex: 1;
            }
            
            .btn-test:hover:not(:disabled) {
                background: #7c3aed;
            }
            
            .btn-test-all {
                background: #f59e0b;
                color: white;
                flex: 1;
            }
            
            .btn-test-all:hover:not(:disabled) {
                background: #d97706;
            }
            
            .btn-refresh {
                background: #6b7280;
                color: white;
                flex: 1;
            }
            
            .btn-refresh:hover:not(:disabled) {
                background: #4b5563;
            }
            
            .tts-controls button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
                transform: none !important;
            }
            
            .tts-info {
                margin-top: 16px;
                padding-top: 12px;
                border-top: 1px solid rgba(255,255,255,0.2);
            }
            
            .engine-stats {
                font-size: 12px;
                opacity: 0.8;
                line-height: 1.4;
            }
            
            .engine-stats p {
                margin: 4px 0;
            }
            
            .engine-stats .stat-line {
                display: flex;
                justify-content: space-between;
            }
            
            .voice-preview {
                margin-top: 8px;
                padding: 8px;
                background: rgba(255,255,255,0.1);
                border-radius: 6px;
                font-size: 11px;
            }
        `;
        
        document.head.appendChild(style);
        
        // Panel in GUI einfügen (nach Voice Assistant Controls)
        const settingsContainer = document.querySelector('.settings-container') || 
                                  document.querySelector('.controls') || 
                                  document.body;
        settingsContainer.appendChild(controlPanel);
        
        // UI-Referenzen speichern
        this.ui = {
            panel: controlPanel,
            engineSelect: document.getElementById('engine-select'),
            voiceSelect: document.getElementById('voice-select'),
            switchEngineBtn: document.getElementById('switch-engine-btn'),
            setVoiceBtn: document.getElementById('set-voice-btn'),
            testTtsBtn: document.getElementById('test-tts-btn'),
            testAllEnginesBtn: document.getElementById('test-all-engines-btn'),
            refreshTtsBtn: document.getElementById('refresh-tts-btn'),
            currentEngineSpan: document.getElementById('tts-current-engine'),
            connectionStatus: document.getElementById('tts-connection-status'),
            engineStats: document.getElementById('engine-stats')
        };
    }
    
    setupEventListeners() {
        // Engine wechseln
        this.ui.switchEngineBtn.addEventListener('click', () => {
            const selectedEngine = this.ui.engineSelect.value;
            if (selectedEngine && selectedEngine !== this.currentEngine) {
                this.switchEngine(selectedEngine);
            }
        });
        
        // Stimme setzen
        this.ui.setVoiceBtn.addEventListener('click', () => {
            const selectedVoice = this.ui.voiceSelect.value;
            if (selectedVoice) {
                this.setVoice(selectedVoice);
            }
        });
        
        // TTS testen
        this.ui.testTtsBtn.addEventListener('click', () => {
            this.testCurrentEngine();
        });
        
        // Alle Engines testen
        this.ui.testAllEnginesBtn.addEventListener('click', () => {
            this.testAllEngines();
        });
        
        // TTS-Info aktualisieren
        this.ui.refreshTtsBtn.addEventListener('click', () => {
            this.refreshTTSInfo();
        });
        
        // Engine-Auswahl Change-Event
        this.ui.engineSelect.addEventListener('change', () => {
            this.updateVoiceSelector();
        });
        
        // WebSocket-Events vom Voice Assistant
        if (this.voiceAssistant) {
            this.voiceAssistant.addEventListener('connected', () => {
                this.onWebSocketConnected();
            });
            
            this.voiceAssistant.addEventListener('disconnected', () => {
                this.onWebSocketDisconnected();
            });
            
            this.voiceAssistant.addEventListener('tts_engine_switched', (event) => {
                this.onEngineSwitch(event.detail);
            });
            
            this.voiceAssistant.addEventListener('tts_info', (event) => {
                this.onTTSInfo(event.detail);
            });
        }
    }
    
    async switchEngine(engineName) {
        if (!this.voiceAssistant || !this.voiceAssistant.isConnected()) {
            this.showMessage('Nicht mit Server verbunden', 'error');
            return;
        }
        
        this.setUIState('switching');
        this.showMessage(`Wechsle zu ${engineName}...`, 'info');
        
        try {
            await this.voiceAssistant.sendMessage({
                type: 'switch_tts_engine',
                engine: engineName
            });
        } catch (error) {
            console.error('Engine switch failed:', error);
            this.showMessage('Engine-Wechsel fehlgeschlagen', 'error');
            this.setUIState('online');
        }
    }
    
    async setVoice(voiceName) {
        if (!this.voiceAssistant || !this.voiceAssistant.isConnected()) {
            this.showMessage('Nicht mit Server verbunden', 'error');
            return;
        }
        
        this.showMessage(`Setze Stimme: ${voiceName}...`, 'info');
        
        try {
            await this.voiceAssistant.sendMessage({
                type: 'set_tts_voice',
                voice: voiceName,
                engine: this.currentEngine
            });
        } catch (error) {
            console.error('Voice change failed:', error);
            this.showMessage('Stimmen-Wechsel fehlgeschlagen', 'error');
        }
    }
    
    async testCurrentEngine() {
        if (!this.voiceAssistant || !this.voiceAssistant.isConnected()) {
            this.showMessage('Nicht mit Server verbunden', 'error');
            return;
        }
        
        const testText = `Dies ist ein Test der ${this.currentEngine} TTS-Engine.`;
        this.showMessage('Teste aktuelle Engine...', 'info');
        
        try {
            await this.voiceAssistant.sendMessage({
                type: 'text',
                content: testText,
                tts_engine: this.currentEngine,
                tts_voice: this.currentVoice
            });
        } catch (error) {
            console.error('TTS test failed:', error);
            this.showMessage('TTS-Test fehlgeschlagen', 'error');
        }
    }
    
    async testAllEngines() {
        if (!this.voiceAssistant || !this.voiceAssistant.isConnected()) {
            this.showMessage('Nicht mit Server verbunden', 'error');
            return;
        }
        
        this.showMessage('Teste alle Engines...', 'info');
        
        try {
            await this.voiceAssistant.sendMessage({
                type: 'test_tts_engines',
                text: 'Dies ist ein Vergleichstest aller TTS-Engines.'
            });
        } catch (error) {
            console.error('TTS test all failed:', error);
            this.showMessage('Engine-Test fehlgeschlagen', 'error');
        }
    }
    
    async refreshTTSInfo() {
        if (!this.voiceAssistant || !this.voiceAssistant.isConnected()) {
            this.showMessage('Nicht mit Server verbunden', 'error');
            return;
        }
        
        try {
            await this.voiceAssistant.sendMessage({
                type: 'get_tts_info'
            });
        } catch (error) {
            console.error('TTS info refresh failed:', error);
            this.showMessage('Info-Aktualisierung fehlgeschlagen', 'error');
        }
    }
    
    onWebSocketConnected() {
        this.setUIState('online');
        this.refreshTTSInfo();
    }
    
    onWebSocketDisconnected() {
        this.setUIState('offline');
        this.resetUI();
    }
    
    onEngineSwitch(data) {
        this.currentEngine = data.engine;
        this.updateCurrentEngineDisplay();
        this.setUIState('online');
        this.showMessage(`Engine gewechselt zu: ${data.engine}`, 'success');
        
        // Voice-Selector aktualisieren
        this.updateVoiceSelector();
    }
    
    onTTSInfo(data) {
        this.availableEngines = data.available_engines || [];
        this.availableVoices = data.available_voices || {};
        this.currentEngine = data.current_engine || 'unknown';
        
        this.updateEngineSelector();
        this.updateVoiceSelector();
        this.updateEngineStats(data.engine_stats);
        this.updateCurrentEngineDisplay();
        
        this.isInitialized = true;
        this.setUIState('online');
    }
    
    updateEngineSelector() {
        this.ui.engineSelect.innerHTML = '';
        
        if (this.availableEngines.length === 0) {
            this.ui.engineSelect.innerHTML = '<option value="">Keine Engines verfügbar</option>';
            return;
        }
        
        this.availableEngines.forEach(engine => {
            const option = document.createElement('option');
            option.value = engine.engine_type;
            option.textContent = `${engine.name} (${engine.engine_type})`;
            if (engine.is_active) {
                option.selected = true;
            }
            this.ui.engineSelect.appendChild(option);
        });
    }
    
    updateVoiceSelector() {
        const selectedEngine = this.ui.engineSelect.value || this.currentEngine;
        this.ui.voiceSelect.innerHTML = '';
        
        if (!selectedEngine || !this.availableVoices[selectedEngine]) {
            this.ui.voiceSelect.innerHTML = '<option value="">Keine Stimmen verfügbar</option>';
            return;
        }
        
        const voices = this.availableVoices[selectedEngine];
        voices.forEach(voice => {
            const option = document.createElement('option');
            option.value = voice;
            option.textContent = voice;
            this.ui.voiceSelect.appendChild(option);
        });
        
        // Aktuelle Stimme auswählen wenn bekannt
        if (this.currentVoice && voices.includes(this.currentVoice)) {
            this.ui.voiceSelect.value = this.currentVoice;
        }
    }
    
    updateEngineStats(stats) {
        if (!stats) {
            this.ui.engineStats.innerHTML = '<p>Keine Statistiken verfügbar</p>';
            return;
        }
        
        let html = '';
        Object.entries(stats).forEach(([engineName, engineStats]) => {
            const avgTime = engineStats.average_processing_time_ms || 0;
            const successRate = engineStats.total_requests > 0 
                ? ((engineStats.successful_requests / engineStats.total_requests) * 100).toFixed(1)
                : 0;
                
            html += `
                <div class="stat-line">
                    <span>${engineName}:</span>
                    <span>${engineStats.total_requests} Requests, ${avgTime.toFixed(1)}ms ⌀, ${successRate}% ✓</span>
                </div>
            `;
        });
        
        this.ui.engineStats.innerHTML = html || '<p>Keine Statistiken verfügbar</p>';
    }
    
    updateCurrentEngineDisplay() {
        this.ui.currentEngineSpan.textContent = this.currentEngine || 'Unbekannt';
    }
    
    setUIState(state) {
        const isOnline = state === 'online';
        const isSwitching = state === 'switching';
        
        // Connection Status
        this.ui.connectionStatus.className = `status-indicator ${state}`;
        
        // Controls aktivieren/deaktivieren
        this.ui.engineSelect.disabled = !isOnline || isSwitching;
        this.ui.voiceSelect.disabled = !isOnline || isSwitching;
        this.ui.switchEngineBtn.disabled = !isOnline || isSwitching;
        this.ui.setVoiceBtn.disabled = !isOnline || isSwitching;
        this.ui.testTtsBtn.disabled = !isOnline || isSwitching;
        this.ui.testAllEnginesBtn.disabled = !isOnline || isSwitching;
        this.ui.refreshTtsBtn.disabled = !isOnline || isSwitching;
        
        // Button-Text für Switching-State
        if (isSwitching) {
            this.ui.switchEngineBtn.textContent = 'Wechselt...';
        } else {
            this.ui.switchEngineBtn.textContent = 'Wechseln';
        }
    }
    
    resetUI() {
        this.availableEngines = [];
        this.availableVoices = {};
        this.currentEngine = 'unknown';
        this.currentVoice = null;
        this.isInitialized = false;
        
        this.ui.engineSelect.innerHTML = '<option value="">Nicht verbunden</option>';
        this.ui.voiceSelect.innerHTML = '<option value="">Nicht verbunden</option>';
        this.ui.engineStats.innerHTML = '<p>Keine Engine-Informationen verfügbar</p>';
        this.updateCurrentEngineDisplay();
    }
    
    showMessage(message, type = 'info') {
        // Integration mit bestehendem Notification-System
        if (window.showNotification) {
            window.showNotification(message, type);
        } else {
            console.log(`[TTS ${type.toUpperCase()}]`, message);
        }
    }
}

// Auto-Initialisierung wenn Voice Assistant verfügbar
document.addEventListener('DOMContentLoaded', () => {
    // Warte auf Voice Assistant Initialisierung
    const initTTSController = () => {
        if (window.voiceAssistant || window.VoiceAssistantCore) {
            const va = window.voiceAssistant || window.VoiceAssistantCore;
            window.ttsController = new TTSEngineController(va);
            console.log('🎤 TTS Engine Controller initialisiert');
        } else {
            // Retry nach 500ms
            setTimeout(initTTSController, 500);
        }
    };
    
    initTTSController();
});

// Export für Modul-System
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TTSEngineController;
}
