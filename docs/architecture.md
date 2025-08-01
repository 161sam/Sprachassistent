# 🏗 Architekturübersicht – Sprachassistent

Diese Datei beschreibt die Systemarchitektur des dezentralen Sprachassistenten, der auf Raspberry Pi, Odroid und einem zentralen Server basiert.

---

## 🎯 Ziel

Ein verteilter Sprachassistent, der lokal Sprache versteht (STT), antwortet (TTS) und komplexe Aufgaben an eine zentrale Automatisierungslogik weiterleitet (n8n, Flowise, lokale LLMs).

---

## 🧱 Komponenten

### 🔊 Raspi 4 (8 GB)

* **STT**: [`faster-whisper`](https://github.com/guillaumekln/faster-whisper)
* **TTS**: [`piper`](https://github.com/rhasspy/piper)
* **Intent-Routing**: Leitet einfache und komplexe Anfragen weiter
* **WebSocket-Server**: `ws-server.py` nimmt Spracheingaben entgegen

### 🧰 Raspi 400 (4 GB)

* **GUI**: Electron-/Web-basierte Steuerung über integrierte Tastatur + Display
* **WebSocket-Client**: sendet Sprache an Raspi 4, empfängt Antwort (Text + Audio)

### 🧠 Odroid N2

* **Flowise (Docker/NPM)**: Agent-basierte LLM-Antwortlogik
* **n8n (Docker/NPM)**: Automatisierungslogik für Smart-Home, Skills etc.

### ☁️ Optionaler Server

* **lokale LLMs**: z. B. GGUF/OpenLLM/LLama.cpp
* **zentrale Flowise-/n8n-Instanzen**

---

## 🔀 Datenflüsse

```mermaid
flowchart LR
  Raspi400 -->|Spracheingabe (Mic)| Raspi4
  Raspi4 -->|Transkript (Text)| Odroid
  Odroid -->|Antwort / Workflow| Raspi4
  Raspi4 -->|Sprachausgabe| Raspi400
```

---

## 🔐 Netzwerk & Sicherheit

* **Tailscale VPN** verbindet alle Geräte sicher
* Token-Auth + IP-Filterung im WS-Server
* Optional: HTTPS mit lokalen Zertifikaten

---

## 🧩 Erweiterbarkeit

* Plugin-System für Skills
* Weitere GUIs (Mobile, Web)
* Mehrere STT/TTS-Knoten

---

## 📦 Projektstruktur (Auszug)

```
cli.sh
config/
docs/
scripts/
ws-server/
voice-assistant-apps/
```

---

## 📌 Nächste Schritte

* Skill-System dokumentieren (`docs/skill-system.md`)
* Netzwerk-Setup in `docs/tailscale-setup.md`
* Routing-Logik in `docs/routing.md`

