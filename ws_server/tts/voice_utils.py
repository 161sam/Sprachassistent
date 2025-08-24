from __future__ import annotations

def canonicalize_voice(v: str | None) -> str | None:
    if not v:
        return v
    return v.strip().replace("de_DE-", "de-")

def expand_aliases(voice_map: dict) -> dict:
    """
    Erzeugt Alias-Keys zur Laufzeit, z.B. 'de_DE-…' für 'de-…',
    ohne sie im JSON vorzuhalten.
    """
    vm = dict(voice_map)
    for key, engines in list(voice_map.items()):
        if key.startswith("de-"):
            alias = key.replace("de-", "de_DE-")
            vm.setdefault(alias, engines)
    return vm
