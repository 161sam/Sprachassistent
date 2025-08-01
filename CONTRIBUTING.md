# 🤝 Contributing to Voice Assistant Apps

Vielen Dank für dein Interesse, zu diesem Projekt beizutragen! Wir freuen uns über jede Art von Beitrag - sei es Code, Dokumentation, Bug-Reports oder Feature-Requests.

## 📋 Inhaltsverzeichnis

- [Code of Conduct](#code-of-conduct)
- [Wie kann ich beitragen?](#wie-kann-ich-beitragen)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Guidelines](#documentation-guidelines)

## 📜 Code of Conduct

Dieses Projekt folgt dem [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). Durch die Teilnahme erwartest du, diesen Code einzuhalten.

### Unsere Standards

**Positives Verhalten:**
- Respektvolle und inklusive Sprache
- Akzeptanz verschiedener Standpunkte
- Konstruktives Feedback geben und annehmen
- Fokus auf das Beste für die Community
- Empathie gegenüber anderen Community-Mitgliedern

**Inakzeptables Verhalten:**
- Beleidigungen oder abwertende Kommentare
- Trolling, beleidigende Kommentare
- Harassment in jeder Form
- Veröffentlichung privater Informationen ohne Erlaubnis

## 🛠️ Wie kann ich beitragen?

### 🐛 Bug Reports

Bevor du einen Bug meldest:
1. **Prüfe bestehende Issues** - vielleicht wurde das Problem bereits gemeldet
2. **Verwende die Issue-Templates** für strukturierte Reports
3. **Füge Details hinzu** - OS, Version, Schritte zur Reproduktion

**Gute Bug Reports enthalten:**
```markdown
**Beschreibung:** Kurze, klare Beschreibung des Problems
**Schritte zur Reproduktion:**
1. Gehe zu '...'
2. Klicke auf '...'
3. Scrolle nach unten zu '...'
4. Siehe Fehler

**Erwartetes Verhalten:** Was sollte passieren
**Aktuelles Verhalten:** Was passiert tatsächlich
**Screenshots:** Falls zutreffend
**Umgebung:**
- OS: [z.B. Windows 11, macOS 13, Android 12]
- App Version: [z.B. 2.1.0]
- Browser: [falls Web-Version]
```

### ✨ Feature Requests

Für neue Features:
1. **Diskutiere zuerst** - öffne ein Discussion bevor du ein Issue erstellst
2. **Erkläre den Nutzen** - warum ist das Feature wertvoll?
3. **Beschreibe die Lösung** - wie sollte es funktionieren?

### 📝 Documentation

- Verbesserungen der README-Dateien
- Tutorials und Guides
- Code-Kommentare
- API-Dokumentation

### 💻 Code Contributions

- Bug Fixes
- Feature Implementierungen
- Performance Verbesserungen
- Refactoring

## 🚀 Development Setup

### Voraussetzungen

```bash
# System Requirements
- Node.js 18+
- NPM 8+
- Git
- Android Studio (für Mobile Development)
```

### Repository Setup

```bash
# 1. Fork das Repository auf GitHub
# 2. Clone dein Fork
git clone https://github.com/DEIN-USERNAME/voice-assistant-apps.git
cd voice-assistant-apps

# 3. Upstream Repository hinzufügen
git remote add upstream https://github.com/ORIGINAL-OWNER/voice-assistant-apps.git

# 4. Dependencies installieren
cd desktop && npm install && cd ..
cd mobile && npm install && cd ..
npm install -g cordova
```

### Development Environment

```bash
# Desktop Development
cd desktop
npm run dev

# Mobile Development
cd mobile
cordova run android

# Docker Development (optional)
docker-compose -f docker-compose.dev.yml up
```

### Branch Strategy

```bash
# Neuen Feature Branch erstellen
git checkout -b feature/awesome-feature

# Oder Bug Fix Branch
git checkout -b fix/bug-description

# Branch-Naming Convention:
# feature/feature-name
# fix/bug-description
# docs/documentation-update
# refactor/component-name
# style/styling-changes
```

## 🔄 Pull Request Process

### 1. Vorbereitung

```bash
# Upstream Changes holen
git fetch upstream
git checkout main
git merge upstream/main

# Deinen Branch aktualisieren
git checkout feature/awesome-feature
git rebase main
```

### 2. Code Quality

```bash
# Linting
npm run lint

# Tests ausführen
npm test

# Build testen
npm run build
```

### 3. Commit Guidelines

Wir verwenden [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Format: type(scope): description

# Beispiele:
git commit -m "feat(desktop): add voice recognition settings"
git commit -m "fix(mobile): resolve audio permission issue"
git commit -m "docs(readme): update installation instructions"
git commit -m "style(ui): improve button hover effects"
git commit -m "refactor(core): extract WebSocket logic"
git commit -m "test(mobile): add speech recognition tests"
```

**Commit Types:**
- `feat`: Neue Features
- `fix`: Bug Fixes
- `docs`: Dokumentation
- `style`: Code Style/Formatting
- `refactor`: Code Refactoring
- `test`: Tests hinzufügen/ändern
- `chore`: Maintenance-Tasks

### 4. Pull Request Erstellen

**PR-Titel:** `type(scope): description`

**PR-Beschreibung Template:**
```markdown
## 📋 Description
Brief description of changes

## 🔄 Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] This change requires a documentation update

## 🧪 Testing
- [ ] Tests pass locally with my changes
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes

## 📝 Checklist
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings

## 📱 Platform Testing
- [ ] Desktop (Electron) - Windows
- [ ] Desktop (Electron) - macOS
- [ ] Desktop (Electron) - Linux
- [ ] Mobile (Android)
- [ ] Mobile (iOS) - if applicable

## 📸 Screenshots
If applicable, add screenshots to help explain your changes.
```

### 5. Review Process

1. **Automatic Checks:** CI/CD Pipeline muss erfolgreich sein
2. **Code Review:** Mindestens 1 Approval von Maintainer
3. **Testing:** Functional Testing auf verschiedenen Platformen
4. **Documentation:** Updates bei Feature-Changes

## 📊 Coding Standards

### JavaScript/TypeScript

```javascript
// ✅ Good
const voiceAssistant = new VoiceAssistantCore();

// Function naming: camelCase
function initializeWebSocket() {
  // Implementation
}

// Constants: UPPER_SNAKE_CASE
const DEFAULT_TIMEOUT = 5000;

// Classes: PascalCase
class VoiceAssistantCore {
  constructor() {
    // Use descriptive names
    this.isRecording = false;
    this.websocketConnection = null;
  }
}
```

### CSS

```css
/* ✅ Good: BEM-like naming */
.voice-assistant__button {
  /* Mobile-first approach */
  padding: 0.5rem;
}

.voice-assistant__button--active {
  background-color: var(--primary-color);
}

@media (min-width: 768px) {
  .voice-assistant__button {
    padding: 1rem;
  }
}
```

### File Organization

```
src/
├── components/          # UI Components
│   ├── VoiceButton/
│   │   ├── index.js
│   │   ├── VoiceButton.js
│   │   └── VoiceButton.css
├── services/           # Business Logic
│   ├── WebSocketService.js
│   └── AudioService.js
├── utils/              # Helper Functions
│   ├── validation.js
│   └── formatting.js
└── constants/          # Constants
    └── config.js
```

## 🧪 Testing Guidelines

### Unit Tests

```javascript
// test/VoiceAssistantCore.test.js
describe('VoiceAssistantCore', () => {
  test('should initialize with correct default settings', () => {
    const assistant = new VoiceAssistantCore();
    expect(assistant.settings.responseNebel).toBe(true);
    expect(assistant.settings.animationSpeed).toBe(1.0);
  });

  test('should handle WebSocket connection', async () => {
    const assistant = new VoiceAssistantCore();
    await assistant.initializeWebSocket();
    expect(assistant.ws).toBeDefined();
  });
});
```

### Integration Tests

```javascript
// test/integration/AudioRecording.test.js
describe('Audio Recording Integration', () => {
  test('should record and send audio to WebSocket', async () => {
    // Mock MediaRecorder
    global.MediaRecorder = jest.fn();
    
    const assistant = new VoiceAssistantCore();
    await assistant.startRecording();
    
    expect(assistant.isRecording).toBe(true);
  });
});
```

### E2E Tests

```javascript
// e2e/VoiceAssistant.e2e.js
describe('Voice Assistant E2E', () => {
  test('should complete full voice interaction', async () => {
    await page.click('#voiceBtn');
    await page.waitForSelector('.recording-indicator.active');
    // Simulate audio input
    await page.click('#voiceBtn'); // Stop recording
    await page.waitForSelector('#response .response-content');
    
    const response = await page.textContent('#response');
    expect(response).not.toBe('Ihre Antwort erscheint hier...');
  });
});
```

## 📚 Documentation Guidelines

### Code Comments

```javascript
/**
 * Initialisiert die WebSocket-Verbindung zum Backend
 * @param {string} url - WebSocket URL (optional)
 * @returns {Promise<WebSocket>} WebSocket-Instanz
 * @throws {Error} Wenn Verbindung fehlschlägt
 */
async function initializeWebSocket(url = null) {
  // Verwende Standard-URL falls keine angegeben
  const wsUrl = url || this.getDefaultWebSocketURL();
  
  try {
    this.ws = new WebSocket(wsUrl);
    return this.ws;
  } catch (error) {
    throw new Error(`WebSocket-Verbindung fehlgeschlagen: ${error.message}`);
  }
}
```

### README Updates

- Neue Features dokumentieren
- Installation/Setup-Schritte aktualisieren
- Screenshots/GIFs für UI-Changes
- Breaking Changes hervorheben

### API Documentation

```javascript
/**
 * @api {websocket} /voice Voice Message
 * @apiName SendVoiceMessage
 * @apiGroup Voice
 * @apiVersion 2.1.0
 * 
 * @apiDescription Sendet Sprach- oder Text-Nachricht an KI-Backend
 * 
 * @apiParam {String} type Nachrichtentyp ("text" oder "audio")
 * @apiParam {String} content Nachrichteninhalt oder Base64-Audio
 * @apiParam {Number} timestamp Unix-Timestamp der Nachricht
 * 
 * @apiSuccess {String} content KI-Antwort
 * @apiSuccess {Object} metadata Zusätzliche Metadaten
 * 
 * @apiExample {json} Text-Nachricht:
 * {
 *   "type": "text",
 *   "content": "Wie ist das Wetter heute?",
 *   "timestamp": 1672531200000
 * }
 */
```

## 🏆 Recognition

Contributors werden in verschiedenen Formen anerkannt:

### All Contributors

Wir verwenden [All Contributors](https://allcontributors.org/) um alle Arten von Beiträgen anzuerkennen:

- 💻 Code
- 📖 Documentation
- 🐛 Bug Reports
- 💡 Ideas
- 🎨 Design
- 📋 Event Organizing
- 💬 Answering Questions

### Hall of Fame

Besondere Beiträge werden in unserer [Hall of Fame](HALL_OF_FAME.md) gewürdigt.

## 📞 Hilfe erhalten

**Wo bekomme ich Hilfe?**

1. **📚 Documentation:** Überprüfe README, BUILD.md und Docs
2. **🔍 Issues:** Suche in bestehenden Issues
3. **💬 Discussions:** GitHub Discussions für Fragen
4. **👥 Community:** Discord/Slack-Channel (falls vorhanden)
5. **📧 Direct Contact:** maintainers@voice-assistant.local

**Vor dem Fragen:**
- Reproduziere das Problem
- Sammle Debug-Informationen
- Beschreibe deine Umgebung
- Teile relevante Code-Snippets

## 🚀 Erste Steps für neue Contributors

1. **🍴 Fork** das Repository
2. **📋 Issue finden** mit Label `good first issue` oder `help wanted`
3. **💬 Kommentieren** im Issue, dass du daran arbeiten möchtest
4. **🏗️ Environment** setup (siehe oben)
5. **💻 Code** schreiben
6. **🧪 Tests** hinzufügen/ausführen
7. **📤 Pull Request** erstellen

### Good First Issues

Perfekt für neue Contributors:
- Documentation improvements
- Simple bug fixes
- Adding tests
- UI/UX improvements
- Translations

## 📄 License

Durch deine Beiträge stimmst du zu, dass deine Arbeit unter der [MIT License](LICENSE) lizenziert wird.

---

**Vielen Dank für deine Beiträge! 🎉**

*Dieses Projekt wird durch Contributors wie dich ermöglicht.*
