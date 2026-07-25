#!/bin/zsh

set -u
PROJECT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
cd -- "$PROJECT_DIR"

pause_for_user() {
  printf "\nPress any key to return to the menu..."
  read -k 1
}

while true; do
  clear
  printf '%s\n' "Lion Marketing Ad Generator"
  printf '%s\n\n' "Choose what you want to do:"
  printf '%s\n' "  1. Edit ad copy"
  printf '%s\n' "  2. Edit brand colors and logo"
  printf '%s\n' "  3. Open design templates"
  printf '%s\n' "  4. Make a quick preview"
  printf '%s\n' "  5. Generate every ad"
  printf '%s\n' "  6. Open finished ads"
  printf '%s\n\n' "  Q. Quit"
  printf "Choice: "
  read -r choice

  case "$choice" in
    1) open "$PROJECT_DIR/1-COPY/ads.csv" ;;
    2) open "$PROJECT_DIR/1-COPY/brand.csv" ;;
    3) open "$PROJECT_DIR/2-TEMPLATES" ;;
    4)
      python3 "$PROJECT_DIR/ad_generator.py" --proof
      pause_for_user
      ;;
    5)
      python3 "$PROJECT_DIR/ad_generator.py"
      pause_for_user
      ;;
    6) mkdir -p "$PROJECT_DIR/3-OUTPUT"; open "$PROJECT_DIR/3-OUTPUT" ;;
    q|Q) exit 0 ;;
    *) printf "\nPlease choose 1-6 or Q."; pause_for_user ;;
  esac
done
