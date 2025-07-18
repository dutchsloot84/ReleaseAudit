#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_DIR="$SCRIPT_DIR/python/python-3.13.5-embed-amd64"
PYTHON_PATH="$PYTHON_DIR/python.exe"
GET_PIP="$PYTHON_DIR/get-pip.py"

PTH_FILE=$(ls "$PYTHON_DIR"/python*._pth 2>/dev/null | head -n 1)
if [ -f "$PTH_FILE" ] && ! grep -q '^import site' "$PTH_FILE"; then
  echo "import site" >> "$PTH_FILE"
fi

if ! "$PYTHON_PATH" -m pip --version >/dev/null 2>&1; then
  echo "Installing pip..."
  "$PYTHON_PATH" "$GET_PIP"
fi

"$PYTHON_PATH" -m pip install --upgrade pip
"$PYTHON_PATH" -m pip install -r "$SCRIPT_DIR/requirements.txt"
