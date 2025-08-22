#!/usr/bin/env python3
"""Repository hygiene checker.

Scans the working tree for legacy server copies, stray backup files and
duplicated TTS engine implementations.  With ``--check`` (default) the
script returns a non-zero exit code when issues are found.  ``--apply``
moves problematic files into ``archive/`` and records a mapping in
``DEPRECATIONS.md``.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import sys
from dataclasses import dataclass
from typing import Iterable, List

# Patterns for legacy or duplicate files
LEGACY_NAMES = {
    "ws-server.py",
    "ws-server-minimal.py",
    "ws-server-enhanced.py",
    "server_enhanced_entry.py",
}
# Backup or stray file patterns
BACKUP_PATTERNS = [
    re.compile(r".*\.bak.*"),
    re.compile(r".*\.orig$"),
    re.compile(r".*\.tmp$"),
    re.compile(r".*\.swp$"),
    re.compile(r".*indentfix.*", re.IGNORECASE),
    re.compile(r".*[_-]fix.*", re.IGNORECASE),
]
BACKEND_BUNDLE = pathlib.Path(
    "voice-assistant-apps/desktop/dist/resources/app/backend"
)
ARCHIVE_ROOT = pathlib.Path("archive")
DEPRECATIONS = pathlib.Path("DEPRECATIONS.md")


@dataclass(frozen=True)
class Issue:
    """Collected hygiene problem."""

    path: pathlib.Path
    reason: str


def find_issues(root: pathlib.Path) -> List[Issue]:
    issues: List[Issue] = []
    tts_defs = {
        "ZonosTTSEngine": re.compile(r"class\s+ZonosTTSEngine"),
        "PiperTTSEngine": re.compile(r"class\s+PiperTTSEngine"),
        "KokoroTTSEngine": re.compile(r"class\s+KokoroTTSEngine"),
    }
    tts_map: dict[str, List[pathlib.Path]] = {cls: [] for cls in tts_defs}

    for path in root.rglob("*"):
        if (root / ARCHIVE_ROOT) in path.parents or "node_modules" in path.parts:
            continue
        if path.is_dir():
            if path.name == "__pycache__":
                issues.append(Issue(path, "PyCache-Verzeichnis"))
            continue
        name = path.name
        if name in LEGACY_NAMES:
            issues.append(Issue(path, "Legacy-Datei"))
            continue
        if any(pat.match(name) for pat in BACKUP_PATTERNS):
            issues.append(Issue(path, "Sicherungsdatei"))
            continue
        if path.suffix == ".pyc":
            issues.append(Issue(path, "Kompilierte Python-Datei"))
            continue
        if path.parts[:2] == ("ws_server", "transport") and "enhanced" in name:
            issues.append(Issue(path, "Veralteter Transport"))
            continue

        if path.suffix == ".py":
            try:
                text = path.read_text(encoding="utf8")
            except Exception:
                continue
            for cls, pattern in tts_defs.items():
                if pattern.search(text):
                    tts_map[cls].append(path)

    for cls, paths in tts_map.items():
        if len(paths) > 1:
            for p in paths:
                issues.append(Issue(p, f"Doppelte TTS-Klasse {cls}"))

    backend_bundle = root / BACKEND_BUNDLE
    if backend_bundle.exists():
        issues.append(Issue(backend_bundle, "Entpacktes Backend-Bundle"))

    issues = sorted(set(issues), key=lambda i: i.path)
    return issues


def move_to_archive(paths: Iterable[pathlib.Path]) -> None:
    ARCHIVE_ROOT.mkdir(exist_ok=True)
    with DEPRECATIONS.open("a", encoding="utf8") as dep:
        for p in paths:
            rel = p.relative_to(pathlib.Path.cwd())
            dest = ARCHIVE_ROOT / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), dest)
            dep.write(f"* {rel} -> {dest}\n")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="move duplicates to archive/")
    parser.add_argument("--check", action="store_true",
                        help="no-op flag for CI compatibility")
    args = parser.parse_args(argv)

    root = pathlib.Path.cwd()
    issues = find_issues(root)
    if issues and args.apply:
        move_to_archive(i.path for i in issues)
        issues = find_issues(root)  # re-scan
    if issues:
        for issue in issues:
            print(f"❌ {issue.reason}: {issue.path}")
        print(f"➡️  {len(issues)} Probleme gefunden.")
        return 1
    print("✅ keine Probleme gefunden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
