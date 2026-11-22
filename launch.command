#!/bin/bash
set -e
cd "$(dirname "$0")"
exec "$HOME/.venvs/f1-reaction-cam/bin/python" app.py "$@"
