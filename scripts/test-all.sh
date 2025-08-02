#!/bin/bash
# Run integration tests for all components
set -e
SCRIPT_DIR=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)
REPO_DIR=$(dirname "$SCRIPT_DIR")
cd "$REPO_DIR"

status=0
for test in test/test_piper.py test/test_kokoro.py test/test_whisper.py test/test_n8n.py test/test_flowise.py test/test_headscale.py; do
  if [ -f "$test" ]; then
    echo "Running $test"
    python "$test" || status=1
  fi
done
exit $status
