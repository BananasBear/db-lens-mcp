#!/usr/bin/env sh
set -eu

APP_NAME="db-lens"
DEFAULT_INSTALL_TARGET="git+https://github.com/MagicPelican/db-lens-mcp.git"
PYTHON_VERSION="${DB_LENS_PYTHON_VERSION:-3.11}"
INSTALL_TARGET="${DB_LENS_INSTALL_TARGET:-$DEFAULT_INSTALL_TARGET}"
DB_LENS_COMMAND="db-lens"

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

install_uv_if_missing() {
  if need_command uv; then
    return
  fi
  info "uv not found. Installing uv..."
  if need_command curl; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  elif need_command python3; then
    python3 -m pip install --user --upgrade uv
  else
    fail "curl or python3 is required to install uv."
  fi
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  need_command uv || fail "uv was installed but is not on PATH. Add $HOME/.local/bin to PATH and retry."
}

install_db_lens() {
  info "Installing ${APP_NAME}..."
  uv tool install --python "$PYTHON_VERSION" --force "$INSTALL_TARGET"
  DB_LENS_COMMAND="$(resolve_db_lens_command)"
}

resolve_db_lens_command() {
  if need_command db-lens; then
    command -v db-lens
    return
  fi
  if [ -n "${UV_TOOL_BIN_DIR:-}" ] && [ -x "$UV_TOOL_BIN_DIR/db-lens" ]; then
    printf '%s\n' "$UV_TOOL_BIN_DIR/db-lens"
    return
  fi
  for candidate in "$HOME/.local/bin/db-lens" "$HOME/.cargo/bin/db-lens"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return
    fi
  done
  fail "db-lens was installed, but its executable was not found. Add uv's tool directory to PATH and retry: export PATH=\"\$HOME/.local/bin:\$HOME/.cargo/bin:\$PATH\""
}

print_next_steps() {
  cat <<EOF

db-lens is installed.

Next steps:
  1. Check the installation:
     $DB_LENS_COMMAND doctor

  2. See available commands:
     $DB_LENS_COMMAND help

  3. Add your database:
     $DB_LENS_COMMAND config add

  4. Connect Codex:
     $DB_LENS_COMMAND mcp install-codex

Restart Codex after install-codex completes.
EOF
  cat <<'EOF'

If `db-lens` is not found in a new terminal, add uv's tool directory to PATH:
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
EOF
}

install_uv_if_missing
install_db_lens
print_next_steps
