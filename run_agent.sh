#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "[ERROR] No virtual environment found. Run venv_start.sh first."
    exit 1
fi

source "$VENV_DIR/bin/activate"

CONFIG="${1:-$SCRIPT_DIR/configs/pokemon_red.json}"
shift 2>/dev/null || true

python "$SCRIPT_DIR/main.py" --config "$CONFIG" "$@"
