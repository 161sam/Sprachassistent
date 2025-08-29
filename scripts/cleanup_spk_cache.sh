#!/usr/bin/env bash
set -euo pipefail

# Cleanup utility to remove accidentally added training/sample files from spk_cache/
# Keeps only a small whitelist of known small files (adjust as needed).

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET_DIR="$REPO_ROOT/spk_cache"

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "spk_cache/ not found at $TARGET_DIR – nothing to do." >&2
  exit 0
fi

# Whitelist (filenames only). Add/remove entries for allowed samples.
KEEP=(
  ".gitkeep"
  "thorsten.wav"
  "thorsten.pt"
)

DRY_RUN=${DRY_RUN:-1}   # set DRY_RUN=0 to actually delete

keep_match() {
  local base="$1"
  for k in "${KEEP[@]}"; do
    if [[ "$base" == "$k" ]]; then return 0; fi
  done
  return 1
}

echo "Scanning $TARGET_DIR …"
removed=0
while IFS= read -r -d '' f; do
  base="$(basename "$f")"
  if keep_match "$base"; then
    echo "keep:   $base"
  else
    if [[ "$DRY_RUN" == "1" ]]; then
      echo "would remove: $base"
    else
      echo "remove: $base"
      rm -f -- "$f" || true
      removed=$((removed+1))
    fi
  fi
done < <(find "$TARGET_DIR" -mindepth 1 -maxdepth 1 -type f -print0)

echo "Done. Removed files: $removed (dry-run=$DRY_RUN)"

