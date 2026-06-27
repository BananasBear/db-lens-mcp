#!/usr/bin/env sh
set -eu

APP_NAME="db-lens"
PYTHON_VERSION="${DB_LENS_PYTHON_VERSION:-3.11}"
INSTALL_TARGET="${DB_LENS_INSTALL_TARGET:-}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

info() {
  printf '%s\n' "$*"
}

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

need_command() {
  command -v "$1" >/dev/null 2>&1
}

detect_target() {
  if [ -n "$INSTALL_TARGET" ]; then
    printf '%s\n' "$INSTALL_TARGET"
    return
  fi
  if [ -f "$PROJECT_DIR/pyproject.toml" ] && grep -q 'name = "db-lens-mcp"' "$PROJECT_DIR/pyproject.toml"; then
    printf '%s\n' "$PROJECT_DIR"
    return
  fi
  printf 'db-lens-mcp\n'
}

install_uv_if_missing() {
  if need_command uv; then
    return
  fi
  info "uv not found. Installing uv with Python user site..."
  need_command python3 || fail "python3 is required to bootstrap uv."
  python3 -m pip install --user --upgrade uv
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  need_command uv || fail "uv was installed but is not on PATH. Add $HOME/.local/bin to PATH and retry."
}

install_db_lens() {
  target="$(detect_target)"
  info "Installing ${APP_NAME} from: ${target}"
  uv tool install --python "$PYTHON_VERSION" --force "$target"
}

print_next_steps() {
  cat <<'EOF'

db-lens is installed.

Next steps:
  1. db-lens doctor
  2. db-lens config add
  3. db-lens mcp config

Paste the JSON printed by `db-lens mcp config` into your AI client's MCP settings.
EOF
}

install_uv_if_missing
install_db_lens
print_next_steps
