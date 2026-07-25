#!/bin/zsh

PROJECT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
cd -- "$PROJECT_DIR"

printf "\nGenerating Lion Marketing ads...\n\n"
python3 "$PROJECT_DIR/ad_generator.py"
status=$?

printf "\nPress any key to close this window..."
read -k 1
exit "$status"
