#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${HOME}/.local/bin"
SCRIPT_NAME="claude-hangul"
ALIAS_LINE="alias claude='claude-hangul'"
ALIAS_TAG="# claude-hangul"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

detect_shell_rc() {
  local shell_name
  shell_name="$(basename "${SHELL:-/bin/bash}")"
  case "$shell_name" in
    zsh)  echo "${HOME}/.zshrc" ;;
    bash)
      if [ -f "${HOME}/.bash_profile" ]; then
        echo "${HOME}/.bash_profile"
      else
        echo "${HOME}/.bashrc"
      fi
      ;;
    fish) echo "${HOME}/.config/fish/config.fish" ;;
    *)    echo "${HOME}/.profile" ;;
  esac
}

add_alias() {
  local rc="$1"
  if [ ! -f "$rc" ]; then
    touch "$rc"
  fi
  if grep -qF "$ALIAS_TAG" "$rc" 2>/dev/null; then
    echo "  alias already in ${rc}"
    return
  fi
  printf '\n%s %s\n' "$ALIAS_LINE" "$ALIAS_TAG" >> "$rc"
  echo "  alias added to ${rc}"
}

remove_alias() {
  local rc="$1"
  if [ ! -f "$rc" ]; then
    return
  fi
  if grep -qF "$ALIAS_TAG" "$rc" 2>/dev/null; then
    # Remove lines containing the tag (compatible with both macOS and GNU sed)
    if sed --version >/dev/null 2>&1; then
      sed -i "/${ALIAS_TAG}/d" "$rc"
    else
      sed -i '' "/${ALIAS_TAG}/d" "$rc"
    fi
    echo "  alias removed from ${rc}"
  fi
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

do_install() {
  local source="${SCRIPT_DIR}/${SCRIPT_NAME}"
  if [ ! -f "$source" ]; then
    echo "Error: ${SCRIPT_NAME} not found in ${SCRIPT_DIR}" >&2
    exit 1
  fi

  mkdir -p "$INSTALL_DIR"
  cp "$source" "${INSTALL_DIR}/${SCRIPT_NAME}"
  chmod +x "${INSTALL_DIR}/${SCRIPT_NAME}"
  echo "Installed ${INSTALL_DIR}/${SCRIPT_NAME}"

  if ! command -v claude &>/dev/null; then
    echo ""
    echo "Warning: 'claude' not found in PATH. Install Claude Code first." >&2
  fi

  local rc
  rc="$(detect_shell_rc)"

  echo ""
  read -rp "Add alias (claude → claude-hangul) to ${rc}? [Y/n] " answer
  case "${answer:-Y}" in
    [Yy]*|"") add_alias "$rc" ;;
    *)        echo "  skipped" ;;
  esac

  echo ""
  echo "Done. Run 'claude-hangul' or open a new shell and run 'claude'."
}

do_uninstall() {
  local did_something=false

  if [ -f "${INSTALL_DIR}/${SCRIPT_NAME}" ]; then
    rm "${INSTALL_DIR}/${SCRIPT_NAME}"
    echo "Removed ${INSTALL_DIR}/${SCRIPT_NAME}"
    did_something=true
  fi

  # Remove alias from all common rc files
  for rc in "${HOME}/.zshrc" "${HOME}/.bashrc" "${HOME}/.bash_profile" \
            "${HOME}/.config/fish/config.fish" "${HOME}/.profile"; do
    if [ -f "$rc" ] && grep -qF "$ALIAS_TAG" "$rc" 2>/dev/null; then
      remove_alias "$rc"
      did_something=true
    fi
  done

  if [ "$did_something" = true ]; then
    echo ""
    echo "Uninstalled. Open a new shell to apply."
  else
    echo "claude-hangul is not installed."
  fi
}

do_status() {
  if [ -f "${INSTALL_DIR}/${SCRIPT_NAME}" ]; then
    echo "Installed: ${INSTALL_DIR}/${SCRIPT_NAME}"
    local rc
    rc="$(detect_shell_rc)"
    if grep -qF "$ALIAS_TAG" "$rc" 2>/dev/null; then
      echo "Alias:     active (${rc})"
    else
      echo "Alias:     not set"
    fi
  else
    echo "Not installed"
  fi
}

usage() {
  cat <<EOF
Usage: install.sh [command]

Commands:
  install     Install claude-hangul and optionally set up alias (default)
  uninstall   Remove claude-hangul and clean up alias
  status      Show installation status
  help        Show this message
EOF
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

case "${1:-install}" in
  install)    do_install ;;
  uninstall)  do_uninstall ;;
  status)     do_status ;;
  help|-h|--help) usage ;;
  *)
    echo "Unknown command: $1" >&2
    usage >&2
    exit 1
    ;;
esac
