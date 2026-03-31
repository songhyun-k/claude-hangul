#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${HOME}/.local/bin"
SCRIPT_NAME="claude-hangul"
SOURCE="$(cd "$(dirname "$0")" && pwd)/${SCRIPT_NAME}"

if [ ! -f "$SOURCE" ]; then
  echo "Error: ${SCRIPT_NAME} not found in $(dirname "$SOURCE")" >&2
  exit 1
fi

mkdir -p "$INSTALL_DIR"
cp "$SOURCE" "${INSTALL_DIR}/${SCRIPT_NAME}"
chmod +x "${INSTALL_DIR}/${SCRIPT_NAME}"

if ! command -v claude &>/dev/null; then
  echo "Warning: 'claude' not found in PATH. Install Claude Code first." >&2
fi

echo "Installed: ${INSTALL_DIR}/${SCRIPT_NAME}"
echo ""
echo "Usage:"
echo "  claude-hangul          # run Claude Code with Korean input fix"
echo ""
echo "Optional alias (add to ~/.zshrc or ~/.bashrc):"
echo "  alias claude='claude-hangul'"
