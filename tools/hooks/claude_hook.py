"""Claude Code hooks for this repo, wired in .claude/settings.json through tools/hooks/run.sh.

after-edit  (PostToolUse on Edit/Write): ruff sorts the imports of the Python file Claude just changed and formats it.
stop-gate   (Stop): if Python files changed and lint, format or the guardrail tests fail, Claude is told what failed
            and asked to fix it before finishing. It never blocks twice in a row, so it can't loop.

Both are local and quick (a few seconds) and never touch the network. Anything unexpected, such as no ruff, no git or
odd input, exits 0: a hook must never get in the way of the person using it.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


def _run(*cmd: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)


def _has(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def after_edit(event: dict) -> int:
    path = Path(event.get("tool_input", {}).get("file_path", ""))
    if path.suffix != ".py" or not path.is_file() or not _has("ruff"):
        return 0
    try:
        path.resolve().relative_to(ROOT)
    except ValueError:
        return 0  # not this repo's file
    # Only sort imports and format. Removing "unused" imports here would delete one an agent added a moment before
    # the edit that uses it; the stop gate and CI still catch any that stay unused.
    _run(PY, "-m", "ruff", "check", "--fix", "--select", "I", "--exit-zero", "--quiet", str(path))
    _run(PY, "-m", "ruff", "format", "--quiet", str(path))
    return 0


def _changed_python_files() -> list[str]:
    out = _run("git", "status", "--porcelain", "--untracked-files=all").stdout
    names = (line[3:].split(" -> ")[-1].strip().strip('"') for line in out.splitlines())
    return [n for n in names if n.endswith(".py") and (ROOT / n).is_file()]


def stop_gate(event: dict) -> int:
    if event.get("stop_hook_active") or not (_has("ruff") and _has("pytest")):
        return 0
    files = _changed_python_files()
    if not files:
        return 0
    problems = []
    lint = _run(PY, "-m", "ruff", "check", "--quiet", *files)
    if lint.returncode:
        problems.append("ruff check:\n" + lint.stdout[-1500:])
    fmt = _run(PY, "-m", "ruff", "format", "--check", "--quiet", *files)
    if fmt.returncode:
        problems.append("ruff format would change:\n" + fmt.stdout[-800:])
    guard = _run(PY, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", "tests/test_guardrails.py")
    if guard.returncode:
        problems.append("tests/test_guardrails.py:\n" + guard.stdout[-2500:])
    if not problems:
        return 0
    print(
        "Before you finish: these checks fail on files you changed. Fix the code, not the checks, "
        "or tell the user why you are stopping.\n\n"
        + "\n\n".join(problems)
        + "\n\nThe full check is `.venv\\Scripts\\python tools\\check.py --fix`.",
        file=sys.stderr,
    )
    return 2  # Claude Code shows this to Claude and lets it continue


def main() -> int:
    try:
        event = json.load(sys.stdin)
        return {"after-edit": after_edit, "stop-gate": stop_gate}[sys.argv[1]](event)
    except Exception:  # noqa: BLE001 - never get in the way
        return 0


if __name__ == "__main__":
    sys.exit(main())
