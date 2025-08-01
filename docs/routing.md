# 🔀 Routing-Logik – Sprachassistent

Diese Datei beschreibt, wie eingehende Spracheingaben in konkrete Aktionen geroutet werden – entweder lokal (Skills) oder extern (n8n / Flowise).

---

## 🧭 Ablaufübersicht

1. Spracheingabe per Mikrofon (GUI / Raspi 400)
2. WebSocket-Verbindung zum Raspi 4
3. Transkription durch Faster-Whisper (STT)
4. Routing-Logik entscheidet:

   * Lokale Reaktion (Skill)
   * Weiterleitung an Flowise Agent (Intent → Text)
   * Auslösen eines n8n Webhook-Workflows
5. Antwort kommt zurück (Text + optional Audio)
6. GUI gibt Antwort aus (Textanzeige, TTS)

---

## 🧠 Entscheidungslogik

```python
if input_text in LOCAL_SKILLS:
    response = run_local_skill(input_text)
elif "frage" in input_text:
    response = ask_flowise(input_text)
else:
    trigger_n8n_workflow(input_text)
    response = "OK, ich habe das erledigt."
```

Die Logik befindet sich in `ws-server.py` unter `IntentRouting`.

---

## ⚙️ Flowise-Weiterleitung

* Flow-ID und Host werden aus `.env` oder den Umgebungsvariablen `FLOWISE_HOST`, `FLOWISE_FLOW_ID` gelesen
* HTTP POST an Flowise REST API
* Antworttext wird an TTS/GUI gesendet

---

## 🔁 n8n-Webhook-Aufruf

* URL wird aus `.env` oder der Umgebungsvariable `N8N_URL` geladen
* Übertragung per `requests.post`
* Eingabe als JSON `{ "query": input_text, "token": WS_TOKEN }`

---

## 🧪 Skill-Shortcuts (local only)

Beispiele:

* "Wie spät ist es?" → Zeit-Plugin
* "Starte Musik" → lokal vordefinierte Aktion
* "Wetter" → Weiterleitung an Flowise

---

## 📌 Weitere Ideen

* Routing über intent.json (Lernbar)
* Priorisierung nach Vertrauen (Score aus STT/LLM)
* Skill-Matching per Regex oder NLP

---

Siehe auch: `docs/skill-system.md` und `ws-server/intent_routing.py`
