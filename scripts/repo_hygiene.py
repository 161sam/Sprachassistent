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
    re.compile(r".*indentfix.*", re.IGNORECASE),
    re.compile(r".*[_-]fix.*", re.IGNORECASE),
]
BACKEND_BUNDLE = pathlib.Path(
    "voice-assistant-apps/desktop/dist/resources/app/backend"
)
ARCHIVE_ROOT = pathlib.Path("archive")
DEPRECATIONS = pathlib.Path("DEPRECATIONS.md")


def find_issues(root: pathlib.Path) -> List[pathlib.Path]:
    issues: List[pathlib.Path] = []
    tts_defs = {
        "ZonosTTSEngine": re.compile(r"class\s+ZonosTTSEngine"),
        "PiperTTSEngine": re.compile(r"class\s+PiperTTSEngine"),
        "KokoroTTSEngine": re.compile(r"class\s+KokoroTTSEngine"),
    }
    tts_map: dict[str, List[pathlib.Path]] = {cls: [] for cls in tts_defs}

    for path in root.rglob("*"):
        if (root / ARCHIVE_ROOT) in path.parents or "node_modules" in path.parts:
            continue
        if not path.is_file():
            continue
        name = path.name
        if name in LEGACY_NAMES:
            issues.append(path)
            continue
        if any(pat.match(name) for pat in BACKUP_PATTERNS):
            issues.append(path)
            continue
        if path.parts[:2] == ("ws_server", "transport") and "enhanced" in name:
            issues.append(path)
            continue

        if path.suffix == ".py":
            try:
                text = path.read_text(encoding="utf8")
            except Exception:
                continue
            for cls, pattern in tts_defs.items():
                if pattern.search(text):
                    tts_map[cls].append(path)

    for paths in tts_map.values():
        if len(paths) > 1:
            issues.extend(paths)

    if BACKEND_BUNDLE.exists():
        issues.append(BACKEND_BUNDLE)

    return sorted(set(issues))


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
        move_to_archive(issues)
        issues = find_issues(root)  # re-scan
    if issues:
        for p in issues:
            print(f"❌ {p}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
