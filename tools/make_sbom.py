"""List the libraries inside a build of DJ Toolkit, as a CycloneDX 1.5 file (docs/releasing.md, "Check a download").

Run by .github/workflows/release.yml on Windows and on macOS, after the build's dependencies are installed and with the
Python the build uses:

    python tools/make_sbom.py DJ-Toolkit-Windows.cdx.json

It asks pip what is installed (`python -m pip inspect`), starts from the packages `requirements.txt` names and follows
each package's own `Requires-Dist` lines to what it needs in turn, so the build tools (PyInstaller, pytest, ruff) are
left out. Python, Qt and ffmpeg are added with the version each one reports. Everything is read from the installed
copies, with no network, and a licence is written only where a package's metadata states one. Standard library only, so
the release job installs nothing new.

Add-ons a package offers ("extras") aren't followed: the app asks for none, and the script stops if that changes.
`build_sbom` is a pure function of what pip reported, so tests/test_make_sbom.py needs no pip.
"""

from __future__ import annotations

import json
import operator
import os
import platform
import re
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "http://cyclonedx.org/schema/bom-1.5.schema.json"


def _key(name: str) -> str:
    """`PySide6_Essentials` and `pyside6-essentials` name the same package: compare without case, `-`, `_` and `.`."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _name_of(requirement: str) -> str:
    found = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[)?", requirement)
    if not found:
        raise ValueError(f"Can't find a package name in {requirement!r}.")
    if found.group(2):
        raise ValueError(f"{requirement.strip()!r} asks for extras, which this script doesn't follow yet.")
    return _key(found.group(1))


def _requirement_names(requirements: str) -> list[str]:
    """The package names in the text of a requirements file."""
    names = []
    for raw in requirements.splitlines():
        line = raw.split("#")[0].strip()
        if line and not line.startswith("-"):  # `-r other.txt` and `--hash=...` lines
            names.append(_name_of(line))
    return names


# --------------------------------------------------------------- environment markers (`python_version < "3.11"`)
_TOKEN = re.compile(r"\s*(\(|\)|\band\b|\bor\b|not\s+in\b|\bin\b|===|~=|==|!=|<=|>=|<|>|'[^']*'|\"[^\"]*\"|\w+)")
_COMPARE = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


def _version(text: str) -> tuple[int, ...] | None:
    return tuple(int(part) for part in text.split(".")) if re.fullmatch(r"\d+(\.\d+)*", text) else None


def _compare(left: str, op: str, right: str) -> bool:
    if op in ("in", "not in"):
        return left in right if op == "in" else left not in right
    a, b = _version(left), _version(right)
    if a is not None and b is not None:  # two version numbers: 3.9 is less than 3.12, and 3.12 equals 3.12.0
        size = max(len(a), len(b))
        return _COMPARE[op](a + (0,) * (size - len(a)), b + (0,) * (size - len(b)))
    return _COMPARE[op](left, right)


def _marker_holds(marker: str, env: Mapping[str, str]) -> bool:
    """Whether an environment marker holds on the machine `env` describes. Raises ValueError if it can't read it."""
    tokens: list[str] = []
    position = 0
    while marker[position:].strip():
        found = _TOKEN.match(marker, position)
        if not found:
            raise ValueError(f"Can't read the marker {marker!r}.")
        tokens.append(found.group(1))
        position = found.end()
    tokens.reverse()  # pop() takes from the end

    def operand() -> str:
        token = tokens.pop()
        return token[1:-1] if token[0] in "'\"" else env[token]

    def atom() -> bool:
        if tokens[-1] == "(":
            tokens.pop()
            inside = either()
            if tokens.pop() != ")":
                raise ValueError(f"Can't read the marker {marker!r}.")
            return inside
        left = operand()
        op = re.sub(r"\s+", " ", tokens.pop())
        return _compare(left, op, operand())

    def both() -> bool:
        result = atom()
        while tokens and tokens[-1] == "and":
            tokens.pop()
            result = atom() and result
        return result

    def either() -> bool:
        result = both()
        while tokens and tokens[-1] == "or":
            tokens.pop()
            result = both() or result
        return result

    try:
        result = either()
    except (IndexError, KeyError) as e:  # ran out of tokens, or a variable pip didn't report
        raise ValueError(f"Can't read the marker {marker!r}.") from e
    if tokens:
        raise ValueError(f"Can't read the marker {marker!r}.")
    return result


# --------------------------------------------------------------------------------------------- the list
def needed_packages(inspected: Mapping, requirements: str) -> dict[str, Mapping]:
    """The installed packages the app needs, by comparable name: what `requirements` names, and what those need."""
    installed = {_key(item["metadata"]["name"]): item["metadata"] for item in inspected["installed"]}
    todo = _requirement_names(requirements)
    for name in todo:
        if name not in installed:
            raise ValueError(f"requirements.txt names {name}, which isn't installed here.")
    needed: dict[str, Mapping] = {}
    while todo:
        name = todo.pop()
        if name in needed:
            continue
        needed[name] = installed[name]
        for requirement in installed[name].get("requires_dist") or []:
            spec, _, marker = requirement.partition(";")
            if re.search(r"\bextra\b", marker):
                continue
            try:
                applies = not marker.strip() or _marker_holds(marker, inspected["environment"])
            except ValueError:
                applies = None  # can't tell: it counts if it is installed
            if applies is False:
                continue
            needs = _name_of(spec)
            if needs not in installed:
                if applies:
                    raise ValueError(f"{name} needs {needs}, which isn't installed here.")
                continue
            todo.append(needs)
    return needed


def _licenses(metadata: Mapping) -> list[dict]:
    """The licence the package's own metadata states: an SPDX expression, or a short name. Some packages put the whole
    licence text in the name field; that isn't a name, so it is left out."""
    if metadata.get("license_expression"):
        return [{"expression": metadata["license_expression"]}]
    name = (metadata.get("license") or "").strip()
    return [{"license": {"name": name}}] if name and "\n" not in name and len(name) <= 100 else []


def _library(metadata: Mapping) -> dict:
    component = {
        "type": "library",
        "name": metadata["name"],
        "version": metadata["version"],
        "purl": f"pkg:pypi/{_key(metadata['name'])}@{quote(metadata['version'], safe='')}",
    }
    if licenses := _licenses(metadata):
        component["licenses"] = licenses
    return component


def build_sbom(
    inspected: Mapping, requirements: str, app_version: str, *, python: str, qt: str, ffmpeg: str, timestamp: str
) -> dict:
    """The CycloneDX document. `inspected` is what `pip inspect` prints; `requirements` is requirements.txt's text."""
    packages = needed_packages(inspected, requirements)
    return {
        "$schema": SCHEMA,
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": timestamp,
            "component": {"type": "application", "name": "DJ Toolkit", "version": app_version},
        },
        "components": [
            *(_library(packages[name]) for name in sorted(packages)),
            {
                "type": "platform",
                "name": "Python",
                "version": python,
                "description": "The Python the build ran on. The app carries it inside.",
            },
            {
                "type": "framework",
                "name": "Qt",
                "version": qt,
                "description": "The version PySide6 reports. Its libraries come inside the PySide6 packages.",
            },
            {
                "type": "application",
                "name": "ffmpeg",
                "version": ffmpeg,
                "description": "The version the imageio-ffmpeg program reports. The app carries it for MP3 export.",
            },
        ],
    }


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Usage: python tools/make_sbom.py OUTPUT.cdx.json", file=sys.stderr)
        return 2
    sys.path.insert(0, str(ROOT))
    import imageio_ffmpeg
    from PySide6 import QtCore

    from djtoolkit import __version__

    # pip prints each package's own text, emoji included, so on Windows it must write UTF-8 into the pipe, not cp1252
    pip = subprocess.run(
        [sys.executable, "-m", "pip", "inspect"],
        stdout=subprocess.PIPE,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=True,
    )
    inspected = json.loads(pip.stdout)
    sbom = build_sbom(
        inspected,
        (ROOT / "requirements.txt").read_text("utf8"),
        __version__,
        python=platform.python_version(),
        qt=QtCore.qVersion(),
        ffmpeg=imageio_ffmpeg.get_ffmpeg_version(),
        timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    Path(argv[0]).write_text(json.dumps(sbom, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {argv[0]}: {len(sbom['components'])} components")
    for component in sbom["components"]:
        print(f"  {component['name']} {component['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
