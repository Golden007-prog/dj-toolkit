#!/usr/bin/env bash
# Runs a Claude Code hook (tools/hooks/claude_hook.py) with the project's own Python.
# No .venv yet? Then there is nothing to check, so it quietly does nothing.
root="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
for py in "$root/.venv/Scripts/python.exe" "$root/.venv/bin/python"; do
  if [ -x "$py" ]; then
    exec "$py" "$root/tools/hooks/claude_hook.py" "$@"
  fi
done
exit 0
