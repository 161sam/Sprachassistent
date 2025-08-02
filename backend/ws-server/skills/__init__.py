from importlib import import_module
from pathlib import Path
from typing import List, Optional

class BaseSkill:
    """Basis-Interface für alle Skills."""
    intent_name: str = "base"

    def can_handle(self, text: str) -> bool:
        raise NotImplementedError

    def handle(self, text: str) -> str:
        raise NotImplementedError

# TODO (docs/skill-system.md §Skills registrieren,
#   docs/Projekt-Verbesserungen.md §Erweiterbares Skill-System):
#   Support plugin discovery and hot-reloading for skills instead of
#   static imports during startup.
def load_all_skills(path: str | Path, enabled: Optional[List[str]] = None) -> List[BaseSkill]:
    """Lade alle Skill-Klassen aus dem angegebenen Verzeichnis."""
    skills: List[BaseSkill] = []
    directory = Path(path)
    for file in directory.glob("*.py"):
        if file.name == "__init__.py" or file.name.startswith("_"):
            continue
        module_name = f"{directory.name}.{file.stem}"
        module = import_module(module_name)
        for obj in module.__dict__.values():
            if isinstance(obj, type) and issubclass(obj, BaseSkill) and obj is not BaseSkill:
                if enabled and obj.__name__ not in enabled:
                    continue
                skills.append(obj())
    return skills
