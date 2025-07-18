#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

"$SCRIPT_DIR/install_requirements.command"

files=()
idx=0
for f in *.csv *.xlsx; do
  if [ -e "$f" ]; then
    idx=$((idx+1))
    files[$idx]="$f"
    echo "  $idx. $f"
  fi
done

if [ "$idx" = "0" ]; then
  echo "No .csv or .xlsx files found in $PWD."
fi

read -p "Enter the number of the file to use, or press Enter to manually input a file path: " choice
if [ -z "$choice" ]; then
  read -p "Enter the path to the Jira file: " filepath
else
  filepath=${files[$choice]}
  if [ -z "$filepath" ]; then
    echo "Invalid choice. Please provide a file path manually."
    read -p "Enter the path to the Jira file: " filepath
  fi
fi

mode_arg=""
echo "Choose run mode:"
echo "  1. Full run (release + develop)"
echo "  2. Develop only"
echo "  3. Release only"
read -p "Enter 1, 2, or 3: " mode
if [ "$mode" = "2" ]; then
  mode_arg="--develop-only"
elif [ "$mode" = "3" ]; then
  mode_arg="--release-only"
fi

PYTHON_PATH="$SCRIPT_DIR/python/python-3.13.5-embed-amd64/python.exe"
export PYTHONPATH="$SCRIPT_DIR"
export REQUESTS_CA_BUNDLE="$SCRIPT_DIR/certs/csaa_netskope_combined.pem"
export SSL_CERT_FILE="$REQUESTS_CA_BUNDLE"

echo "Running:"
echo "$PYTHON_PATH $SCRIPT_DIR/main.py --jira-excel \"$filepath\" $mode_arg"
"$PYTHON_PATH" "$SCRIPT_DIR/main.py" --jira-excel "$filepath" $mode_arg
