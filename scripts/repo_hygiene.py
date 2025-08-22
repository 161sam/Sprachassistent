#!/usr/bin/env python3
"""Repository hygiene checker.

Scans the working tree for legacy server copies, backup files and
mispackaged backend duplicates. With ``--check`` (default) the script
returns a non-zero exit code when issues are found. ``--apply`` moves
problematic files into ``archive/`` and records a mapping in
``DEPRECATIONS.md``.
"""

from __future__ import annotations

import argparse
import pathlib
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
SUFFIXES = [".bak", "_fix", "_indentfix", "_binary_migration"]
BACKEND_BUNDLE = pathlib.Path(
    "voice-assistant-apps/desktop/dist/resources/app/backend"
)
ARCHIVE_ROOT = pathlib.Path("archive")
DEPRECATIONS = pathlib.Path("DEPRECATIONS.md")


def find_issues(root: pathlib.Path) -> List[pathlib.Path]:
    issues: List[pathlib.Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if (root / ARCHIVE_ROOT) in path.parents or "node_modules" in path.parts:
            continue
        name = path.name
        if name in LEGACY_NAMES or any(name.endswith(s) for s in SUFFIXES):
            issues.append(path)
    if BACKEND_BUNDLE.exists():
        issues.append(BACKEND_BUNDLE)
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
        move_to_archive(issues)
        issues = find_issues(root)  # re-scan
    if issues:
        for p in issues:
            print(f"❌ {p}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
