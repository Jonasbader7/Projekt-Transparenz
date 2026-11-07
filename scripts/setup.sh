#!/usr/bin/env bash
# Einrichtung unter Linux/macOS (z. B. GitHub Codespaces). Windows: scripts/setup.ps1
set -euo pipefail
cd "$(dirname "$0")/.."
VENV="${1:-.venv}"
[ -x "$VENV/bin/python" ] || python3.12 -m venv "$VENV"
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet -e ".[dev]"
"$VENV/bin/python" -m transparenz init-db
"$VENV/bin/python" -m transparenz update --force
echo "Fertig. App starten mit: $VENV/bin/python -m streamlit run app/main.py"
