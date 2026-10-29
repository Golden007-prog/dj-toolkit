"""Guardrails: the project's written rules, as tests.

Docs drift; tests hold. Each test enforces one rule from AGENTS.md or docs/ux/VOICE.md, so a person or an AI agent
who breaks it finds out in seconds, with a message that says what to do instead.

If a rule is wrong, change it in the docs and here, in the same pull request, and say why. Never weaken a check just
to get a green run.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
from functools import cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "djtoolkit"
UI = PKG / "ui"


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _py_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*.py") if "__pycache__" not in p.parts)


@cache
def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text("utf8"), filename=str(path))


@cache
def _repo_files() -> tuple[Path, ...]:
    """Every file git would commit: tracked, plus new files that .gitignore doesn't exclude."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    return tuple(ROOT / f for f in out.decode("utf8").split("\0") if f and (ROOT / f).is_file())


# ------------------------------------------------------------- architecture
def test_audio_and_spotify_logic_never_import_qt():
    """The core is plain Python (NumPy, requests), so it is fast to test and reusable. Qt lives in djtoolkit/ui only."""
    core = [p for p in _py_files(PKG) if UI not in p.parents]
    bad = []
    for path in core:
        for node in ast.walk(_tree(path)):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                mods = [("." * node.level) + (node.module or "")]
            for m in mods:
                if m.startswith("PySide6") or m.lstrip(".").startswith("ui") or ".ui" in m:
                    bad.append(f"{_rel(path)}:{node.lineno} imports {m}")
    assert not bad, (
        "Core modules must not depend on Qt or the UI. Pass callbacks in, like spotify/engine.run_sync does:\n"
        + "\n".join(bad)
    )


HEX = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")


def test_colours_come_only_from_the_theme():
    """A hard-coded colour breaks Booth, Daylight or an accent. Read theme.P.<role> instead."""
    bad = []
    for path in _py_files(UI):
        if path.name == "theme.py":
            continue
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and HEX.search(node.value):
                bad.append(f"{_rel(path)}:{node.lineno}  {node.value[:60]!r}")
    assert not bad, (
        "Hard-coded colours. Use theme.P.<role>; if no role fits, add one to every palette in ui/theme.py "
        "(tests/test_theme.py then checks its contrast):\n" + "\n".join(bad)
    )


def test_file_dialogs_go_through_the_remembering_helpers():
    """Every dialog reopens where the user left off, with a fallback if that folder is gone."""
    bad = []
    for path in _py_files(PKG):
        if path == UI / "dialogs.py":
            continue
        for node in ast.walk(_tree(path)):
            name = getattr(node, "id", None) or getattr(node, "attr", None) or getattr(node, "name", None)
            if name == "QFileDialog":
                bad.append(f"{_rel(path)}:{node.lineno}")
    assert not bad, "Use ui/dialogs.pick_file or pick_dir, not QFileDialog directly:\n" + "\n".join(bad)


def test_known_qt_traps_stay_fixed():
    """Each of these broke the app once (AGENTS.md, "Qt gotchas")."""
    bad = []
    for path in _py_files(ROOT / "djtoolkit") + _py_files(ROOT / "tools"):
        for node in ast.walk(_tree(path)):
            where = f"{_rel(path)}:{getattr(node, 'lineno', '?')}"
            if isinstance(node, ast.Attribute) and node.attr == "startfile":
                bad.append(
                    f"{where} os.startfile exists only on Windows, so it crashes on macOS. "
                    "Use QDesktopServices.openUrl(QUrl.fromLocalFile(...))."
                )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "setButtonSymbols" and "NoButtons" in ast.unparse(node):
                    bad.append(
                        f"{where} setButtonSymbols(NoButtons) collapses a styled spin box to 1 px. "
                        "Zero the buttons in QSS instead (see QDoubleSpinBox#bpm in ui/theme.py)."
                    )
                if node.func.attr == "setGraphicsEffect":
                    bad.append(
                        f"{where} a QGraphicsEffect re-renders its widget on every repaint (the waveform "
                        "repaints 30 times a second). widgets.Panel paints its own shadow."
                    )
            if (
                isinstance(node, ast.BinOp)
                and isinstance(node.op, ast.LShift)
                and isinstance(node.right, ast.BinOp)
                and isinstance(node.right.op, (ast.Add, ast.Sub))
            ):
                bad.append(f"{where} `a << b + c` shifts by (b + c). Write `(a << b) + c`.")
            if isinstance(node, ast.Constant) and node.value == "offscreen" and path.parent.name == "tools":
                bad.append(
                    f"{where} the offscreen Qt platform renders without fonts on Windows. Lay the window out "
                    "with WA_DontShowOnScreen instead (see tools/screenshots.py)."
                )
    assert not bad, "\n".join(bad)


# ---------------------------------------------------------------- the voice
# User-facing text follows docs/ux/VOICE.md: plain words a DJ uses, no hype, no software jargon.
BANNED = [
    r"\boops\b", r"\bwhoops\b", r"\bawesome\b", r"\bunfortunately\b", r"\binvalid\b", r"\billegal\b",
    r"\bclick here\b", r"\berror occurred\b", r"\bsuccess\b", r"\bwe\b",
    r"\btokens?\b", r"\boauth\b", r"\bpkce\b", r"\bcach(e|ed|es|ing)\b", r"\bthresholds?\b", r"\bdry run\b",
    r"\bauthori[sz]\w*", r"\bmirror mode\b", r"\blookups?\b", r"\bpreroll\b", r"\blead-in\b",
    r"\bwarp markers?\b", r"\banchor points?\b",
]  # fmt: skip
BANNED_RE = re.compile("|".join(BANNED), re.IGNORECASE)
EMOJI = re.compile("[\U0001f000-\U0001faff☀-➿️]")

# Messages that predate this check: the Spotify activity log, the browser page after linking, and two errors.
# A good first issue (docs/roadmap.md). Reword one, then delete its line: the test fails until you do,
# so this list only ever gets shorter. Never add to it.
KNOWN_COPY_DEBT = {
    ("djtoolkit/spotify/auth.py", "Token request failed"),
    ("djtoolkit/spotify/auth.py", "Authorized. You can close this tab"),
    ("djtoolkit/spotify/auth.py", "Authorization failed. You can close this tab."),
    ("djtoolkit/spotify/auth.py", "Opening your browser to authorize Spotify"),
    ("djtoolkit/spotify/auth.py", "Spotify authorization failed: "),
    ("djtoolkit/spotify/auth.py", "Saved login expired; re-authorizing."),
    ("djtoolkit/spotify/engine.py", " fresh lookups this run (cached tracks are free)."),
    ("djtoolkit/spotify/engine.py", " searches cached)"),
    ("djtoolkit/spotify/engine.py", "Progress is cached."),
    ("djtoolkit/spotify/engine.py", "Dry run complete. No changes made."),
}


def _docstring_ids(tree: ast.Module) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                ids.add(id(first.value))
    return ids


def _copy_strings() -> list[tuple[str, int, str]]:
    """String literals a user could read: anything with a space in it that isn't a docstring.
    (Identifiers, keys, file names, URLs and icon names have no spaces.)"""
    found = []
    for path in _py_files(PKG):
        tree = _tree(path)
        skip = _docstring_ids(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
                if " " in node.value.strip():
                    found.append((_rel(path), node.lineno, node.value))
    tutorials = ROOT / "assets" / "tutorials" / "tutorials.json"
    for t in json.loads(tutorials.read_text("utf8")):
        for text in (t["title"], t["recommendation"], *t["steps"]):
            found.append((_rel(tutorials), 0, text))
    return found


FILE_NAME = re.compile(r"\.?[\w-]+\.[A-Za-z]\w{1,4}\b|(?<![\w.])\.[A-Za-z]\w+")  # search-cache.json, .env, .cache


def _voice_problems(text: str) -> list[str]:
    words = FILE_NAME.sub(" ", text)  # naming a file the user has to pick is fine
    problems = [f"says {m.group(0)!r}" for m in BANNED_RE.finditer(words)]
    if re.search(r"!(?!=)", text):
        problems.append("has an exclamation mark")
    if EMOJI.search(text):
        problems.append("has an emoji (use an icon from ui/icons.py)")
    return problems


def test_ui_text_follows_the_voice_guide():
    new, seen = [], set()
    for file, line, text in _copy_strings():
        problems = _voice_problems(text)
        if not problems:
            continue
        debt = next((k for k in KNOWN_COPY_DEBT if k[0] == file and k[1] in text), None)
        if debt:
            seen.add(debt)
            continue
        new.append(f"{file}:{line}  {text[:70]!r}  {', '.join(problems)}")
    assert not new, (
        "This text doesn't follow docs/ux/VOICE.md (see its glossary and 'Words and habits to avoid'):\n"
        + "\n".join(new)
    )
    fixed = KNOWN_COPY_DEBT - seen
    assert not fixed, f"Fixed, thank you. Now delete these from KNOWN_COPY_DEBT: {sorted(fixed)}"


def test_the_voice_check_catches_what_it_should():
    assert _voice_problems("Oops! Something went wrong") == ["says 'Oops'", "has an exclamation mark"]
    assert _voice_problems("Authorize with your token") == ["says 'Authorize'", "says 'token'"]
    assert _voice_problems("Saved. Ready for the USB.") == []
    assert _voice_problems("Done \U0001f389") == ["has an emoji (use an icon from ui/icons.py)"]
    assert _voice_problems("Pick the search-cache.json from the old tool's .cache folder.") == []
    assert _voice_problems("Reads 128.00 BPM. Downbeat at 1.200 s.") == []


# ------------------------------------------------------------ repo hygiene
PERSONAL_PATH = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"'<>%*]+|/Users/[^/\s\"'<>*]+/|/home/[^/\s\"'<>*]+/")
SECRET = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----"  # private keys
    r"|\bgh[pousr]_[A-Za-z0-9]{36}\b"  # GitHub tokens
    r"|\bsk-ant-[A-Za-z0-9_-]{20,}"  # Anthropic keys
    r"|\bAKIA[0-9A-Z]{16}\b"  # AWS keys
    r"|\bxox[abprs]-[A-Za-z0-9-]{10,}"  # Slack tokens
)
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".toml", ".yml", ".yaml", ".bat", ".cfg", ".ini",
                 ".astro", ".css", ".js", ".mjs", ".ts", ".html", ".svg"}  # fmt: skip
NEVER_COMMIT = {".env", "token.json", "search-cache.json", "discussions.json"}


def test_no_secrets_or_personal_paths_are_committed():
    """Keys belong in %APPDATA%, never in the repo. Absolute paths from your machine leak your name and break for
    everyone else: use paths relative to the repo, or %APPDATA% / ~ in docs."""
    bad = []
    for path in _repo_files():
        rel = _rel(path)
        if path.name in NEVER_COMMIT or path.name.startswith(".env."):
            bad.append(f"{rel}: this file holds personal data or keys; it is git-ignored for a reason")
            continue
        if path.name == "settings.json" and rel != ".claude/settings.json":
            bad.append(f"{rel}: app settings hold personal paths; keep them in %APPDATA%\\DJToolkit")
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES or path == Path(__file__):
            continue
        text = path.read_text("utf8", errors="replace")
        for regex, what in ((SECRET, "a secret key"), (PERSONAL_PATH, "a personal path")):
            for m in regex.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                bad.append(f"{rel}:{line}: {what}: {m.group(0)[:40]}")
    assert not bad, "\n".join(bad)


def test_no_large_files():
    """Clones stay fast. Shrink images (WebP, ~1600 px wide) or keep big files out of git."""
    big = [f"{_rel(p)} ({p.stat().st_size // 1024} KB)" for p in _repo_files() if p.stat().st_size > 800 * 1024]
    assert not big, "Files over 800 KB:\n" + "\n".join(big)


MD_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)|!\[[^\]]*\]\(([^)\s]+)\)")


def test_links_between_docs_point_to_real_files():
    """Renaming or moving a file? Update the docs that link to it."""
    files = _repo_files()
    known = {_rel(p) for p in files}
    folders = {str(Path(k).parent.as_posix()) for k in known} | {p.as_posix() for k in known for p in Path(k).parents}
    bad = []
    for md in (p for p in files if p.suffix == ".md"):
        text = re.sub(r"```.*?```", "", md.read_text("utf8"), flags=re.S)  # examples in code blocks don't count
        for m in MD_LINK.finditer(text):
            target = (m.group(1) or m.group(2)).split("#")[0]
            if not target or re.match(r"[a-z][a-z0-9+.-]*:", target, re.I):
                continue  # anchors, http:, mailto:
            resolved = (md.parent / target).resolve()
            try:
                rel = resolved.relative_to(ROOT).as_posix()
            except ValueError:
                bad.append(f"{_rel(md)} -> {target} (outside the repo)")
                continue
            if rel not in known and rel not in folders:
                bad.append(f"{_rel(md)} -> {target}")
    assert not bad, "Broken links (the target isn't in the repo):\n" + "\n".join(bad)
