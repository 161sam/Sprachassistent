from importlib import import_module, reload
from pathlib import Path
from typing import List, Optional
import pkgutil

class BaseSkill:
    """Basis-Interface für alle Skills."""
    intent_name: str = "base"

    def can_handle(self, text: str) -> bool:
        raise NotImplementedError

    def handle(self, text: str) -> str:
        raise NotImplementedError

def _discover_modules(path: Path) -> List[str]:
    return [name for _, name, _ in pkgutil.iter_modules([str(path)])]


def load_all_skills(path: str | Path, enabled: Optional[List[str]] = None) -> List[BaseSkill]:
    """Lade alle Skill-Klassen und unterstütze Hot-Reloading."""
    skills: List[BaseSkill] = []
    directory = Path(path)
    for name in _discover_modules(directory):
        if name.startswith("_"):
            continue
        module_name = f"{directory.name}.{name}"
        module = import_module(module_name)
        module = reload(module)
        for obj in module.__dict__.values():
            if isinstance(obj, type) and issubclass(obj, BaseSkill) and obj is not BaseSkill:
                if enabled and obj.__name__ not in enabled:
                    continue
                skills.append(obj())
    return skills


def reload_skills(path: str | Path, enabled: Optional[List[str]] = None) -> List[BaseSkill]:
    """Convenience wrapper to reload skills during runtime."""
    return load_all_skills(path, enabled)
