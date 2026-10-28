"""Run every check CI runs, in the order that fails fastest. Run it before you push, and have your AI agent run it
before it says a change is done.

    .venv\\Scripts\\python tools\\check.py            lint, format, then the full test suite (about a minute)
    .venv\\Scripts\\python tools\\check.py --fix      let ruff fix what it can first
    .venv\\Scripts\\python tools\\check.py -- -k sync pass anything after `--` to pytest (here: only tests matching "sync")
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

HINTS = {
    "lint": "Run `python tools/check.py --fix`, then fix what is left by hand. The message names the rule.",
    "format": "Run `python tools/check.py --fix` (or `ruff format .`). Formatting is never worth arguing about.",
    "tests": (
        "Read the first failure. Guardrail tests (tests/test_guardrails.py) say which rule they enforce and what to "
        "do instead. Fix the code, not the test."
    ),
}


def run(title: str, cmd: list[str]) -> bool:
    print(f"\n== {title}", flush=True)
    started = time.monotonic()
    ok = subprocess.run(cmd, cwd=ROOT).returncode == 0
    print(f"-- {title}: {'ok' if ok else 'FAILED'} ({time.monotonic() - started:.0f} s)", flush=True)
    return ok


def main(argv: list[str]) -> int:
    extra = argv[argv.index("--") + 1 :] if "--" in argv else []
    steps: list[tuple[str, list[str]]] = []
    if "--fix" in argv:
        steps += [
            ("fix", [PY, "-m", "ruff", "check", "--fix", "--quiet", "."]),
            ("reformat", [PY, "-m", "ruff", "format", "--quiet", "."]),
        ]
    steps += [
        ("lint", [PY, "-m", "ruff", "check", "."]),
        ("format", [PY, "-m", "ruff", "format", "--check", "."]),
        ("tests", [PY, "-m", "pytest", "-q", *extra]),
    ]
    for title, cmd in steps:
        if not run(title, cmd):
            if title in HINTS:
                print(f"\nNext step: {HINTS[title]}")
            return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
