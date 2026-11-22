#!/bin/bash
set -e
cd "$(dirname "$0")"
venv="$HOME/.venvs/f1-reaction-cam"
if [ ! -x "$venv/bin/python" ]; then
    python3.11 -m venv "$venv"
fi
"$venv/bin/python" -m pip install --only-binary=:all: -r requirements.txt
"$venv/bin/python" -m pip check
"$venv/bin/python" setup_models.py
