#!/bin/bash
set -e
PROFILE=""
SCOPE="all"
while [[ $# -gt 0 ]]; do
  case $1 in
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --scope)
      SCOPE="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
python testsuite/run.py --scope "$SCOPE" ${PROFILE:+--profile "$PROFILE"}
