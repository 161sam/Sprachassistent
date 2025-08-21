# AGENTS – Project Guide for AI Assistants

## Project Overview  
**Sprachassistent** is a modular voice assistant platform with a local backend (Raspberry Pi/Odroid hardware) and cross-platform client apps. It performs speech recognition (STT) and speech synthesis (TTS) entirely on-device, without cloud services. The system can intelligently route user commands either to built-in local skills, to an integrated LLM agent, or to automation workflows depending on the intent. Client applications (Desktop Electron, Android Cordova, and Web GUI) connect to the backend via WebSockets to send audio and receive text/audio responses in real time.

## Architecture & Core Components  
- **Speech-to-Text (STT):** Uses the **Faster-Whisper** engine (CTranslate2 Whisper model) for offline transcription. All voice input is transcribed locally; no external STT API is used.  
- **Text-to-Speech (TTS):** Supports multiple TTS engines, with **Zonos** as the default. Additional engines **Piper** and **Kokoro** are available, and the system can switch engines at runtime.  
- **Intent Routing:** After transcription, text is routed based on intent:  
  - If it matches a local **skill**, a skill plugin handles it.  
  - If it’s a general query, it’s forwarded to an **LLM agent** (via Flowise).  
  - If it triggers automation, it’s passed to an **n8n workflow**.  
- **LLM Agent Integration:** Flowise AI flows handle complex queries by calling language models and returning results.  
- **Automation Workflows:** n8n workflows can be triggered for actions such as smart home control or external integrations.  
- **Client Interface:** Electron desktop, Cordova mobile, and web-based GUIs capture audio, send it to the backend, and play back TTS audio responses.  

## Setup & Usage  
1. **Install Dependencies:**  
   - Backend: `pip install -r requirements.txt`  
   - Client: `npm install` inside `voice-assistant-apps/`  

2. **Configuration:**  
   - Copy `.env.example` → `.env` and adjust.  
   - Required: `WS_HOST`, `WS_PORT`, `STT_MODEL`, `STT_DEVICE`, `TTS_ENGINE`.  
   - Defaults are provided in `.env.defaults`, `.env`  

3. **Run Backend:**  
   ```bash
   python backend/ws-server/ws-server.py
   ```

4. **Run App:**  
   ```bash
    cd voice-assistant-apps/desktop && npm start 
   ```

