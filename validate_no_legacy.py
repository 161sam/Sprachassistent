#!/usr/bin/env python3
import pathlib, sys, re

ROOT = pathlib.Path(__file__).resolve().parent
bad_patterns = [r"\bbackend\.", r"\bws_server\.compat\b", r"\blegacy_ws_server\b"]

violations = []
for py in ROOT.rglob("*.py"):
    if py.parts[0] in ("archive","archive_legacy",".venv"): 
        continue
    txt = py.read_text(encoding="utf-8", errors="ignore")
    for pat in bad_patterns:
        if re.search(pat, txt):
            violations.append((py, pat))

if violations:
    print("❌ Legacy imports detected:")
    for v in violations:
        print(" -", v[0], "matches", v[1])
    sys.exit(1)

print("✅ No legacy imports detected.")

