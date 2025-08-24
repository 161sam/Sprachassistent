#!/usr/bin/env bash
set -euo pipefail

TARGET="archive_legacy"
mkdir -p "$TARGET"

FILES=(
  "backend"
  "cli.py"
  "sprachassistent/cli.py"
  "phonemizer_local"
  $(find . -name "*.bak*" -o -name "*.bak" || true)
  "tests/unit/test_legacy_ws_streaming.py"
)

echo "📦 Preparing to move legacy files into $TARGET"
for f in "${FILES[@]}"; do
  if [ -e "$f" ]; then
    echo " - $f"
    if [ "${1:-}" != "--dry-run" ]; then
      mv "$f" "$TARGET"/
    fi
  fi
done
echo "✅ Done. Legacy files moved to $TARGET (use --dry-run for simulation)."

