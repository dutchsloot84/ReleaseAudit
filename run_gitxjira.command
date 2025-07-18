#!/bin/bash

# Determine the directory of this script so it can be run from anywhere
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

shopt -s nullglob
FILES=( *.csv *.xlsx )
IDX=0
for f in "${FILES[@]}"; do
    IDX=$((IDX + 1))
    printf "  %d. %s\n" "$IDX" "$f"
done

if [ "$IDX" -eq 0 ]; then
    echo "No .csv or .xlsx files found in $PWD."
fi

read -r -p "Enter the number of the file to use, or press Enter to manually input a file path: " CHOICE
if [ -z "$CHOICE" ]; then
    read -r -e -p "Enter the path to the Jira file: " FILEPATH
else
    IDX=$((CHOICE - 1))
    if [ $IDX -ge 0 ] && [ $IDX -lt ${#FILES[@]} ]; then
        FILEPATH="${FILES[$IDX]}"
    else
        echo "Invalid choice. Please provide a file path manually."
        read -r -e -p "Enter the path to the Jira file: " FILEPATH
    fi
fi

MODE_ARG=""

echo "Choose run mode:"
echo "  1. Full run (release + develop)"
echo "  2. Develop only"
echo "  3. Release only"
read -r -p "Enter 1, 2, or 3: " MODE
if [ "$MODE" = "2" ]; then
    MODE_ARG="--develop-only"
elif [ "$MODE" = "3" ]; then
    MODE_ARG="--release-only"
fi

echo "Running:"
echo python3 "$SCRIPT_DIR/main.py" --jira-excel "$FILEPATH" $MODE_ARG
python3 "$SCRIPT_DIR/main.py" --jira-excel "$FILEPATH" $MODE_ARG
