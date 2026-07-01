#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/.."
VENV_DIR="$ROOT_DIR/.venv"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "[ERROR] No virtual environment found. Run venv_start.sh first."
    exit 1
fi

source "$VENV_DIR/bin/activate"

CONFIG="${1:-$ROOT_DIR/configs/default.json}"
shift 2>/dev/null || true

python "$ROOT_DIR/main.py" --config "$CONFIG" "$@"
