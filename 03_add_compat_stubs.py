#!/usr/bin/env python3
"""
Fügt kleine Kompatibilitäts-Stubs ein, ohne Logik zu ändern.
- Exportiert in ws_server/metrics/__init__.py eine bequeme Factory
- Ergänzt docstrings & NOOP-Funktionen, falls einzelne Attribute fehlen
"""
from pathlib import Path

root = Path("ws_server")

# metrics/__init__.py: einfache Factories re-exportieren
metrics_init = root / "metrics" / "__init__.py"
if metrics_init.exists():
    txt = metrics_init.read_text(encoding="utf-8")
else:
    txt = "# package\n"
if "def get_metrics_api" not in txt:
    txt += """

def get_metrics_api(voice_server=None):
    try:
        from .http_api import MetricsAPI
        return MetricsAPI(voice_server)
    except Exception:
        return None
"""
    metrics_init.write_text(txt, encoding="utf-8")

print("✅ Compat-Stubs ergänzt.")

