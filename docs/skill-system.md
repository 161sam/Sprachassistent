# Skill-System

Der WebSocket-Server lädt zur Laufzeit Skills aus dem Ordner
`backend/ws-server/skills`. Jeder Skill implementiert die Klasse
`BaseSkill` und kann so modular erweitert werden.

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
