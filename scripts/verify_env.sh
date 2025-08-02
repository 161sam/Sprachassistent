#!/bin/bash
# Simple environment validator
set -e
ENV_FILE=${1:-.env}
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ $ENV_FILE not found"
  exit 1
fi

set -a
. "$ENV_FILE"
set +a

echo "Validating environment from $ENV_FILE"

while IFS='=' read -r key value; do
  [[ -z "$key" || "$key" =~ ^# ]] && continue
  val=${!key}
  if [ -z "$val" ]; then
    echo "❌ $key is unset"
    continue
  fi
  if [[ "$val" =~ ^https?:// ]]; then
    if curl -fsS "$val" >/dev/null 2>&1; then
      echo "✅ $key reachable at $val"
    else
      echo "❌ $key not reachable at $val"
    fi
  elif [[ "$val" =~ / || "$val" =~ \.onnx$ || "$val" =~ model\.json$ ]]; then
    if [ -e "$val" ]; then
      echo "✅ $key found at $val"
    else
      echo "❌ $key path missing at $val"
    fi
  else
    echo "✅ $key is present"
  fi
done < "$ENV_FILE"
