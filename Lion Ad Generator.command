#!/bin/zsh

PROJECT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
cd -- "$PROJECT_DIR"

python3 "$PROJECT_DIR/app_server.py" --open --quiet
status=$?

if (( status != 0 )); then
  printf "\nThe app could not start. Make sure Python 3 is installed.\n"
  printf "Press any key to close this window..."
  read -k 1
fi
exit "$status"
