#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Repository hygiene & archival for the Sprachassistent repo.

- Erkennt Backup-/Alt-/Obsolete-Dateien & -Ordner:
  *.bak.*, *.back*, *.backup*, *.old, *.orig, *.disabled, *~, *.tmp, *.swp, *.swo, *.rej
- Verschiebt Funde nach archive/ (aktuelle Altlasten) oder archive_legacy/
  (explizit alte/legacy/bak/backup/obsolete Inhalte).
- Protokolliert Moves in DEPRECATIONS.md mit Grund.
- Erkennt Repo-Root automatisch (Ordnername "Sprachassistent" oder Marker-Dateien).
- Optional: entfernt leere Verzeichnisse (--prune-empty-dirs).

Beispiele:
  python scripts/repo_hygiene.py --check
  python scripts/repo_hygiene.py --apply
  python scripts/repo_hygiene.py --apply --prune-empty-dirs
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
import re
import shutil
import sys
from dataclasses import dataclass
from typing import Iterable, List, Tuple

# ---------- Repo-Root-Erkennung ----------
REPO_NAME_HINT = "Sprachassistent"
ROOT_MARKERS = {
    "pyproject.toml",
    "requirements.txt",
    "README.md",
    "scripts/repo_hygiene.py",
}

# ---------- Ziele ----------
ARCHIVE = pathlib.Path("archive")
ARCHIVE_LEGACY = pathlib.Path("archive_legacy")
DEPRECATIONS = pathlib.Path("DEPRECATIONS.md")

# ---------- Ignorierbereiche ----------
SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "desktop-build",
    "venv",
}
SKIP_ROOTS = {ARCHIVE.name, ARCHIVE_LEGACY.name}

# ---------- Erkennungsregeln ----------
BACKUP_FILE_PATTERNS: Tuple[re.Pattern, ...] = (
    re.compile(r".*\.bak(\.|$)", re.IGNORECASE),
    re.compile(r".*\.back(\.|$)", re.IGNORECASE),
    re.compile(r".*\.backup(\.|$)", re.IGNORECASE),
    re.compile(r".*\.old(\.|$)", re.IGNORECASE),
    re.compile(r".*\.orig(\.|$)", re.IGNORECASE),
    re.compile(r".*\.disabled(\.|$)", re.IGNORECASE),
    re.compile(r".*~$"),                 # Editor-Backups
    re.compile(r".*\.tmp$"),             # Tempfiles
    re.compile(r".*\.swp$|.*\.swo$"),    # Vim-Swap
    re.compile(r".*\.rej$"),             # Patch rejections
)

OUTDATED_DIR_TOKENS = {"backup", "backups", "old", "obsolete", "unused", "legacy"}
OUTDATED_NAME_TOKENS = {
    "bak", "backup", "back", "old", "obsolete", "unused", "legacy", "deprecated",
}

LEGACY_FILENAMES = {
    "ws-server.py",
    "ws-server-minimal.py",
    "ws-server-enhanced.py",
    "server_enhanced_entry.py",
}

BACKEND_BUNDLE = pathlib.Path(
    "voice-assistant-apps/desktop/dist/resources/app/backend"
)


@dataclass(frozen=True)
class Issue:
    path: pathlib.Path
    reason: str
    to_legacy: bool  # True -> archive_legacy, False -> archive


def is_repo_root(p: pathlib.Path) -> bool:
    if p.name == REPO_NAME_HINT:
        return True
    for marker in ROOT_MARKERS:
        if (p / marker).exists():
            return True
    return False


def find_repo_root(start: pathlib.Path) -> pathlib.Path:
    cur = start.resolve()
    while True:
        if is_repo_root(cur):
            return cur
        if cur.parent == cur:
            return start.resolve()  # Fallback: nimm Startpunkt
        cur = cur.parent


def is_backup_file(name: str) -> bool:
    return any(p.search(name) for p in BACKUP_FILE_PATTERNS)


def contains_outdated_token(name: str) -> bool:
    low = name.lower()
    return any(tok in low for tok in OUTDATED_NAME_TOKENS)


def path_has_outdated_dir_token(path: pathlib.Path) -> bool:
    return any(seg.lower() in OUTDATED_DIR_TOKENS for seg in path.parts)


def classify(path: pathlib.Path) -> tuple[bool, str, bool]:
    """
    Liefert (is_issue, reason, to_legacy)
    """
    name = path.name
    if path.is_symlink():
        return (False, "", False)

    if name in LEGACY_FILENAMES:
        return (True, "Legacy-Datei", True)

    if path.suffix == ".pyc":
        return (True, "Kompilierte Python-Datei", False)

    if is_backup_file(name):
        reason = "Backup-/Altdatei"
        to_legacy = True if ("bak" in name.lower() or "legacy" in name.lower()) else False
        return (True, reason, to_legacy)

    if contains_outdated_token(name):
        return (True, "Veralteter Dateiname", True)

    if path_has_outdated_dir_token(path):
        return (True, "In veraltetem Ordner", True)

    if path == BACKEND_BUNDLE:
        return (True, "Entpacktes Desktop-Backend-Bundle", False)

    return (False, "", False)


def should_skip_dir(path: pathlib.Path) -> bool:
    segs = set(path.parts)
    if segs & SKIP_ROOTS:
        return True
    if any(seg in SKIP_DIR_NAMES for seg in path.parts):
        return True
    if path.name == "__pycache__":
        return True
    return False


def find_issues(root: pathlib.Path) -> List[Issue]:
    issues: List[Issue] = []
    for path in root.rglob("*"):
        # Bereiche archiv/legacy überspringen
        if any((root / skip) in path.parents for skip in (ARCHIVE, ARCHIVE_LEGACY)):
            continue
        if any(seg in SKIP_DIR_NAMES for seg in path.parts):
            continue

        try:
            is_dir = path.is_dir()
            is_file = path.is_file()
        except OSError:
            continue

        if is_dir:
            continue
        if not is_file:
            continue

        is_issue, reason, to_legacy = classify(path)
        if is_issue:
            issues.append(Issue(path, reason, to_legacy))

    # Dedup + Sort
    seen = set()
    uniq: List[Issue] = []
    for i in sorted(issues, key=lambda x: str(x.path)):
        key = (str(i.path), i.reason, i.to_legacy)
        if key not in seen:
            uniq.append(i)
            seen.add(key)
    return uniq


def ensure_parent(dest: pathlib.Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)


def unique_dest(dest: pathlib.Path) -> pathlib.Path:
    """Verhindere Überschreiben im Archiv."""
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    idx = 1
    while True:
        cand = parent / f"{stem}__{idx}{suffix}"
        if not cand.exists():
            return cand
        idx += 1


def choose_archive(issue: Issue, root: pathlib.Path) -> pathlib.Path:
    rel = issue.path.relative_to(root)
    base = ARCHIVE_LEGACY if issue.to_legacy else ARCHIVE
    return (root / base / rel).resolve()  # <-- neu: absolut


def move_to_archives(issues: Iterable[Issue], root: pathlib.Path) -> List[Tuple[pathlib.Path, pathlib.Path, str]]:
    ARCHIVE.mkdir(exist_ok=True)
    ARCHIVE_LEGACY.mkdir(exist_ok=True)
    moved: List[Tuple[pathlib.Path, pathlib.Path, str]] = []
    for i in issues:
        dest = choose_archive(i, root)       # <-- absolut
        ensure_parent(dest)
        dest = unique_dest(dest)             # bleibt absolut
        shutil.move(str(i.path), str(dest))  # i.path ist absolut, dest nun auch
        moved.append((i.path, dest, i.reason))
    return moved


def write_deprecations(moved: List[Tuple[pathlib.Path, pathlib.Path, str]], root: pathlib.Path) -> None:
    if not moved:
        return
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with (root / DEPRECATIONS).open("a", encoding="utf8") as f:
        f.write(f"\n## Repo hygiene run at {now}\n\n")
        for src, dst, reason in moved:
            try:
                rel_src = src.relative_to(root)
            except ValueError:
                rel_src = pathlib.Path(os.path.relpath(str(src), str(root)))
            try:
                rel_dst = dst.relative_to(root)
            except ValueError:
                rel_dst = pathlib.Path(os.path.relpath(str(dst), str(root)))
            f.write(f"* {rel_src} ➜ {rel_dst} — {reason}\n")


def prune_empty_dirs(root: pathlib.Path) -> int:
    """Leere Ordner (außer archive*/.git/node_modules etc.) entfernen."""
    removed = 0
    for d in sorted((p for p in root.rglob("*") if p.is_dir()),
                    key=lambda p: len(p.parts),
                    reverse=True):
        if d.name in SKIP_DIR_NAMES or d.name in SKIP_ROOTS:
            continue
        if any((root / skip) in d.parents for skip in (ARCHIVE, ARCHIVE_LEGACY)):
            continue
        try:
            if not any(d.iterdir()):
                d.rmdir()
                removed += 1
        except OSError:
            continue
    return removed


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sprachassistent repo hygiene & archival")
    parser.add_argument("--apply", action="store_true", help="Verschiebe Funde nach archive*/ und schreibe DEPRECATIONS.md")
    parser.add_argument("--check", action="store_true", help="Nur prüfen (Default-Verhalten, kompatibel zu CI)")
    parser.add_argument("--prune-empty-dirs", action="store_true", help="Nach --apply leere Verzeichnisse löschen")
    parser.add_argument("--root", type=str, default=".", help="Startpfad (Repo-Root wird automatisch hochwärts gesucht)")
    parser.add_argument("--verbose", action="store_true", help="Ausführliche Ausgabe im --check Modus")
    args = parser.parse_args(argv)

    start = pathlib.Path(args.root).resolve()
    root = find_repo_root(start)
    os.chdir(root)

    issues = find_issues(root)

    # Immer eine Zusammenfassung ausgeben (auch wenn 0 Funde)
    print(f"[repo_hygiene] Root: {root}")
    print(f"[repo_hygiene] Gefundene Kandidaten: {len(issues)}")

    if issues and args.apply:
        moved = move_to_archives(issues, root)
        write_deprecations(moved, root)
        if args.prune_empty_dirs:
            removed = prune_empty_dirs(root)
            print(f"🧹 Leere Verzeichnisse entfernt: {removed}")
        # Nach dem Move erneut scannen
        issues = find_issues(root)

    if issues:
        # Ausgabe der Treffer (im Check-Modus ggf. ausführlich)
        for issue in issues:
            target = choose_archive(issue, root)
            line = f"❌ {issue.reason}: {issue.path}  →  {target}"
            if args.verbose or not args.apply:
                print(line)
        print(
            f"➡️  {len(issues)} Problem(e) gefunden. "
            f"(Dry-Run: verwende --apply zum Verschieben)"
        )
        return 1

    print("✅ Keine Probleme gefunden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
