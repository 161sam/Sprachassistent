#!/usr/bin/env python3
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent

SKIP_DIRS = {
    ".venv", "venv", "__pycache__",
    "archive", "archive_legacy",
    "externals",  # third-party
    "tests", "test", "testsuite",  # unit/integration tests
}
# Wir behalten den Compat-Baum, scannen ihn aber nicht: Ziel ist produktiver Code
SKIP_DIRS.add(pathlib.Path("ws_server/compat").as_posix())

BAD = [
    r"\bbackend\.",           # alte Backend-Imports
    r"\bws_server\.compat\b", # Kompat-Layer
    r"\blegacy_ws_server\b",  # alter Servername
]

def should_skip(p: pathlib.Path) -> bool:
    try:
        rel = p.relative_to(ROOT)
    except ValueError:
        return True
    parts = rel.parts
    return any(part in SKIP_DIRS for part in parts)

violations = []
for path in ROOT.rglob("*.py"):
    if should_skip(path):
        continue
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for pat in BAD:
        if re.search(pat, txt):
            violations.append((str(path), pat))

if violations:
    print("❌ Legacy-Referenzen gefunden:")
    for p, pat in violations:
        print(f" - {p}  (match: {pat})")
    sys.exit(1)

print("✅ Keine Legacy-Referenzen gefunden (produktiver Code).")
