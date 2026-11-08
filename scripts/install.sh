#!/usr/bin/env bash
# Install `coordinator` as a user-level command (no root).
#   scripts/install.sh              editable install (default; code changes apply immediately)
#   scripts/install.sh --copy       regular install (repo can be moved/deleted afterwards)
#   scripts/install.sh --uninstall  remove the command
# Uses uv if present, else pipx. Needs Python >= 3.11. Exit: 0 ok, 1 failure, 2 usage.
set -euo pipefail
cd "$(dirname "$0")/.."

mode=editable
case "${1:-}" in
  "") ;;
  --copy) mode=copy ;;
  --uninstall) mode=uninstall ;;
  -h|--help) sed -n '2,5p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) echo "usage: $0 [--copy|--uninstall]" >&2; exit 2 ;;
esac

if command -v uv >/dev/null 2>&1; then
  case "$mode" in
    editable)  uv tool install --force --editable . ;;
    copy)      uv tool install --force . ;;
    uninstall) uv tool uninstall coordinator ;;
  esac
elif command -v pipx >/dev/null 2>&1; then
  case "$mode" in
    editable)  pipx install --force --editable . ;;
    copy)      pipx install --force . ;;
    uninstall) pipx uninstall coordinator ;;
  esac
else
  echo "error: need uv (https://docs.astral.sh/uv/) or pipx installed" >&2
  exit 1
fi

[ "$mode" = uninstall ] && { echo "coordinator removed"; exit 0; }

if command -v coordinator >/dev/null 2>&1; then
  echo "installed: $(command -v coordinator)"
else
  echo "installed, but ~/.local/bin is not on PATH; add it to your shell profile" >&2
fi
