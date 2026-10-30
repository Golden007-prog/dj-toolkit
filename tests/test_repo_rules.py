"""The repository's own rules: who approves what, what Dependabot may merge alone, and that every dependency has a
documented reason. GitHub enforces the rest (docs/maintaining.md); these catch a change here that would quietly
break it."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITHUB = ROOT / ".github"
DEPENDENCIES_PAGE = ROOT / "docs" / "dependencies.md"


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


def _package_key(name: str) -> str:
    """`PySide6`, `pyside6` and `Imageio_FFmpeg` name the same Python package: compare without case, `-`, `_` and `.`."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _declared_packages() -> dict[str, tuple[str, str]]:
    """Every direct dependency: its comparable name -> (the name as written, the file that names it)."""
    declared = {}
    for path in sorted(ROOT.glob("requirements*.txt")):
        for line in path.read_text("utf8").splitlines():
            line = line.split("#")[0].strip()
            if line and not line.startswith("-"):  # `-r requirements.txt` pulls in another file
                found = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*([=<>!~;@]|$)", line)
                assert found, f"{path.name}: can't find a package name in {line!r}"
                declared.setdefault(_package_key(found.group(1)), (found.group(1), path.name))
    site = json.loads((ROOT / "website" / "package.json").read_text("utf8"))
    for name in [*site.get("dependencies", {}), *site.get("devDependencies", {})]:
        declared.setdefault(_package_key(name), (name, "website/package.json"))
    return declared


def _documented_packages() -> dict[str, tuple[str, list[str]]]:
    """Each row of docs/dependencies.md: its comparable name -> (the name as written, the other cells)."""
    rows = {}
    for line in DEPENDENCIES_PAGE.read_text("utf8").splitlines():
        if re.match(r"\|\s*`[^`]+`\s*\|", line):  # the header and the divider have no backticks
            name, *cells = (cell.strip() for cell in line.strip().strip("|").split("|"))
            rows[_package_key(name.strip("`"))] = (name.strip("`"), cells)
    return rows


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


def test_only_dependabots_minor_and_patch_updates_merge_without_the_owner():
    """What an agent writes, Copilot included, waits for a person: no other workflow approves or merges."""
    offenders = []
    for flow in sorted((GITHUB / "workflows").glob("*.yml")):
        if flow.name != "dependabot-auto-merge.yml":
            if re.search(
                r"gh pr merge|gh pr review\b[^\n]*--approve|--auto\b|enablePullRequestAutoMerge", flow.read_text("utf8")
            ):
                offenders.append(flow.name)
    assert not offenders, f"only dependabot-auto-merge.yml may approve or merge a pull request: {offenders}"


def test_every_action_is_pinned_to_a_full_commit_sha():
    """A tag can be moved to other code, a commit can't. Local actions (./...) are exempt."""
    unpinned = []
    for flow in sorted((GITHUB / "workflows").glob("*.y*ml")):
        for number, line in enumerate(flow.read_text("utf8").splitlines(), 1):
            used = re.match(r"\s*(?:- )?uses:\s*(\S+)", line)
            if used and not used.group(1).startswith("./") and not re.search(r"@[0-9a-f]{40}$", used.group(1)):
                unpinned.append(f"{flow.name}:{number}: {used.group(1)}")
    assert not unpinned, "pin each action to a 40-character commit SHA, version as a comment:\n" + "\n".join(unpinned)


def test_every_pre_commit_hook_repository_is_pinned_to_a_full_commit_sha():
    """The hooks run on a contributor's machine at every commit, and a tag can be moved to other code, a commit can't."""
    unpinned = []
    revs = 0
    for number, line in enumerate((ROOT / ".pre-commit-config.yaml").read_text("utf8").splitlines(), 1):
        rev = re.match(r"\s*rev:\s*(\S+)(.*)", line)
        if rev:
            revs += 1
            if not (
                re.fullmatch(r"[0-9a-f]{40}", rev.group(1)) and re.fullmatch(r"\s*# frozen: v?\d\S*", rev.group(2))
            ):
                unpinned.append(f".pre-commit-config.yaml:{number}: {line.strip()}")
    assert revs, "no `rev:` found in .pre-commit-config.yaml: has the file changed shape?"
    assert not unpinned, (
        "pin each hook repository to a 40-character commit SHA, `# frozen: vX.Y.Z` after it:\n" + "\n".join(unpinned)
    )


def test_the_dependency_guard_watches_every_dependency_file_and_cannot_be_edited_by_a_pull_request():
    flow = (GITHUB / "workflows" / "dependency-guard.yml").read_text("utf8")
    watched = re.search(r'^\s+deps="([^"]+)"$', flow, re.M).group(1).split()
    assert sorted(watched) == _dependency_files(), "the guard must watch exactly the files CODEOWNERS leaves unowned"
    folders = re.search(r'^\s+dirs="([^"]+)"', flow, re.M)
    assert folders and folders.group(1).split() == ["tools/deps/"] and (ROOT / "tools" / "deps").is_dir(), (
        "the guard must watch the lists the requirements are built from"
    )
    assert "pull_request_target" in flow, "it must run from main, so a pull request can't change what it checks"
    assert "actions/checkout" not in flow, "it must never check out the pull request's code"
    assert 'context="Dependency files"' in flow
    scripts = [step.split("run: |", 1)[1] for step in flow.split("- name: ")[1:] if "run: |" in step]
    assert scripts and not any("${{" in script for script in scripts), "event data goes through env:, never a script"


def test_every_issue_form_waits_for_triage():
    forms = [f for f in sorted((GITHUB / "ISSUE_TEMPLATE").glob("*.yml")) if f.name != "config.yml"]
    assert forms
    for form in forms:
        labels = re.search(r"^labels: \[(.*)\]$", form.read_text("utf8"), re.M)
        assert labels and '"needs triage"' in labels.group(1), form.name


def test_every_dependency_has_a_documented_row():
    documented = _documented_packages()
    missing = [f"  {name} (in {file})" for key, (name, file) in _declared_packages().items() if key not in documented]
    assert not missing, (
        "A dependency needs a documented reason. Add one row to docs/dependencies.md for each of these:\n"
        + "\n".join(missing)
        + "\nWrite what it is for, its licence, who publishes it and where its source is, and the date it was checked "
        "(docs/maintaining.md, 'Auditing an outside pull request', step 6)."
    )


def test_every_documented_dependency_is_still_used():
    declared = _declared_packages()
    stale = [name for key, (name, _) in _documented_packages().items() if key not in declared]
    assert not stale, (
        "docs/dependencies.md has a row for a package that no dependency file names any more: "
        + ", ".join(stale)
        + ".\nDelete the row, or put the package back if you removed it by mistake."
    )


def test_every_dependency_row_is_filled_in():
    unfinished = [name for name, cells in _documented_packages().values() if len(cells) != 4 or not all(cells)]
    assert not unfinished, (
        "These rows in docs/dependencies.md need all five cells filled in (Package, Used for, Licence, "
        "Publisher and source repository, Checked): " + ", ".join(unfinished)
    )


def test_a_workflow_on_pull_request_target_never_checks_out_the_pull_request():
    """pull_request_target hands a fork's pull request a token that can write, so nothing in the workflow may fetch
    or run the pull request's code. A script it needs comes from main (see pr-assignment.yml)."""
    offenders = []
    for flow in sorted((GITHUB / "workflows").glob("*.yml")):
        code = re.sub(r"#.*", "", flow.read_text("utf8"))  # what a workflow says about itself in comments is fine
        # Reading a commit's SHA through the API (.head.sha) is fine; fetching or checking out its code is not.
        if re.search(r"\bpull_request_target\b", code) and re.search(
            r"actions/checkout|pull_request\.head|head_ref|refs/pull|gh pr checkout|gh repo clone|git (?:fetch|clone)",
            code,
        ):
            offenders.append(flow.name)
    assert not offenders, f"a pull_request_target workflow must not check out the pull request's code: {offenders}"
