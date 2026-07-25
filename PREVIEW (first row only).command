#!/bin/zsh

PROJECT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
cd -- "$PROJECT_DIR"

printf "\nRendering the first copy row in every design and size...\n\n"
python3 "$PROJECT_DIR/ad_generator.py" --proof
status=$?

printf "\nPress any key to close this window..."
read -k 1
exit "$status"
