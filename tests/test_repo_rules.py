"""The repository's own rules: who approves what, and what Dependabot may merge alone. GitHub enforces the rest
(docs/maintaining.md); these catch a change here that would quietly break it."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITHUB = ROOT / ".github"


def _dependency_files() -> list[str]:
    files = [*ROOT.glob("requirements*.txt"), ROOT / "website" / "package.json", ROOT / "website" / "package-lock.json"]
    return sorted(p.relative_to(ROOT).as_posix() for p in files)


def _codeowners() -> list[tuple[str, list[str]]]:
    rules = []
    for line in (GITHUB / "CODEOWNERS").read_text("utf8").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            pattern, *owners = line.split()
            rules.append((pattern, owners))
    return rules


def _dependabot() -> dict[tuple[str, str], str]:
    """Each update block of dependabot.yml, keyed by (ecosystem, directory)."""
    text = (GITHUB / "dependabot.yml").read_text("utf8")
    blocks = {}
    for block in re.split(r"^\s*- package-ecosystem: ", text, flags=re.M)[1:]:
        directory = re.search(r"^\s+directory: (\S+)", block, re.M)
        blocks[(block.split()[0], directory.group(1) if directory else "")] = block
    return blocks


def test_the_owner_approves_everything_but_the_dependency_files():
    rules = _codeowners()
    assert rules[0] == ("*", ["@tomgreef"]), "the first rule must give every file an owner"
    unowned = sorted(pattern.lstrip("/") for pattern, owners in rules if not owners)
    assert unowned == _dependency_files(), "only dependency files may merge on Dependabot's approval alone"


def test_dependabot_watches_every_kind_of_dependency():
    assert {("pip", "/"), ("npm", "/website"), ("github-actions", "/")} <= set(_dependabot())


def test_only_minor_and_patch_updates_are_grouped():
    for key, block in _dependabot().items():
        assert re.search(r"update-types: \[minor, patch\]", block), f"{key}: majors must stay out of the group"
        assert "cooldown:" in block, f"{key}: new releases should wait a few days"


def test_major_updates_never_merge_themselves():
    flow = (GITHUB / "workflows" / "dependabot-auto-merge.yml").read_text("utf8")
    merge = next(step for step in flow.split("- name: ") if "gh pr merge --auto" in step)
    condition = re.search(r"if: (.+)", merge).group(1)
    assert "semver-minor" in condition and "semver-patch" in condition and "semver-major" not in condition


def test_every_issue_form_waits_for_triage():
    forms = [f for f in sorted((GITHUB / "ISSUE_TEMPLATE").glob("*.yml")) if f.name != "config.yml"]
    assert forms
    for form in forms:
        labels = re.search(r"^labels: \[(.*)\]$", form.read_text("utf8"), re.M)
        assert labels and '"needs triage"' in labels.group(1), form.name
