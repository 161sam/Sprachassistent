# Skill-System

Der WebSocket-Server lädt zur Laufzeit Skills aus dem Ordner
`skills`. Jeder Skill implementiert die Klasse
`BaseSkill` und kann so modular erweitert werden. Eine ML-gestützte
Intent-Klassifikation entscheidet standardmäßig, welcher Skill aktiv ist.
Fällt das Modell aus, greift eine Schlüsselwort-Heuristik als Fallback.

```python
class BaseSkill:
    intent_name: str = "base"
    def can_handle(self, text: str) -> bool: ...
    def handle(self, text: str) -> str: ...
```

## Skills registrieren

Alle `.py`-Dateien in `skills/` werden automatisch geladen. Über die
Umgebungsvariable `ENABLED_SKILLS` kann die Auswahl eingeschränkt
werden:

```
ENABLED_SKILLS=TimeSkill,GreetingSkill
```

## Beispiel

`skills/time_skill.py`:

```python
from datetime import datetime
from . import BaseSkill

class TimeSkill(BaseSkill):
    intent_name = "time_query"

    def can_handle(self, text: str) -> bool:
        return "zeit" in text

    def handle(self, text: str) -> str:
        return f"Es ist {datetime.now().strftime('%H:%M')} Uhr."
```

Neue Dateien nach diesem Muster ablegen, schon stehen sie dem
Sprachassistenten ohne weitere Änderungen zur Verfügung.

### Intent-Klassifikation

Bei jeder Texteingabe bestimmt ein ML-Modell das passende
Intent-Label (z. B. `time_query` oder `greeting`). Das Ergebnis wird
für die Skill-Auswahl genutzt. Ist kein Modell vorhanden, wird eine
Schlüsselwort-basierte Fallback-Erkennung verwendet.
