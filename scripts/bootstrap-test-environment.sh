#!/usr/bin/env bash
set -euo pipefail

# Coreless reproducible development/test environment bootstrap.
# Prepares dependencies only; it does not install model weights.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null || { echo "ERROR: python3 is required."; exit 1; }
"$PYTHON" -m venv .coreless-venv
source .coreless-venv/bin/activate
python -m pip install --upgrade pip
if [[ -f requirements.txt ]]; then python -m pip install -r requirements.txt; fi
echo "Coreless test environment prepared: $ROOT/.coreless-venv"
echo "No model weights were downloaded."