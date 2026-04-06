#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ -f venv/bin/activate ]]; then
  # shellcheck source=/dev/null
  source venv/bin/activate
fi
exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8011
