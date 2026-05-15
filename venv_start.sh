#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "[INFO] No .venv found at $VENV_DIR"
    read -rp "Create a new virtual environment here? [y/N] " reply
    case "$reply" in
        [yY]|[yY][eE][sS]) ;;
        *) exit 1 ;;
    esac
    python3 -m venv "$VENV_DIR"
    echo "[OK] Virtual environment created"
fi

source "$VENV_DIR/bin/activate"
echo "[OK] Activated: $VENV_DIR"

if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    echo "[INFO] Installing requirements..."
    pip install -r "$SCRIPT_DIR/requirements.txt"
fi
