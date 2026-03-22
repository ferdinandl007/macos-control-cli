#!/usr/bin/env bash
# desktop-control — thin wrapper that invokes cli.py via the project venv
set -euo pipefail

VENV="$HOME/.openclaw/tools/desktop-control/.venv"
# Resolve symlinks to find the real script directory
REAL_PATH="$(readlink -f "$0" 2>/dev/null || python3 -c "import os; print(os.path.realpath('$0'))")"
SCRIPT_DIR="$(cd "$(dirname "$REAL_PATH")" && pwd)"
CLI="$SCRIPT_DIR/cli.py"

exec "$VENV/bin/python" "$CLI" "$@"
