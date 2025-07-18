#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_PATH="$SCRIPT_DIR/python/python-3.13.5-embed-amd64/python.exe"
GET_PIP="$SCRIPT_DIR/python/python-3.13.5-embed-amd64/get-pip.py"

if ! "$PYTHON_PATH" -m pip --version >/dev/null 2>&1; then
  echo "Installing pip..."
  "$PYTHON_PATH" "$GET_PIP"
fi

"$PYTHON_PATH" -m pip install --upgrade pip
"$PYTHON_PATH" -m pip install -r "$SCRIPT_DIR/requirements.txt"
