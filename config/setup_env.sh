#!/bin/bash
# Simple helper to switch environment profiles
# Usage: ./config/setup_env.sh <profile>
# Copies config/.env.<profile> to project root .env
set -e
if [ -z "$1" ]; then
  echo "Usage: $0 <profile>"
  exit 1
fi
cp "config/.env.$1" .env
echo "🔄 Environment switched to: $1"
