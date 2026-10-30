# Maintaining

For maintainers and the owner: what GitHub enforces, and the routine jobs. Who can do what, and how people join:
[GOVERNANCE.md](../GOVERNANCE.md).

## What GitHub enforces

Three rulesets (*Settings > Rules > Rulesets*):

| Ruleset | What it does | Who can skip it |
|---|---|---|
| **Checks must pass** (`main`) | Nothing lands until these are green: `App on windows-latest (lint, format, tests)`, `App on macos-latest (lint, format, tests)`, `App on ubuntu-latest (lint, format, tests)`, `Website (build)`, `Dependency review`, `Workflow security (zizmor)`, `Workflow syntax (actionlint)` and `Dependency files`. No force pushes, and `main` can't be deleted | Nobody |
| **A code owner approves** (`main`) | Changes arrive by pull request, with an approval from a code owner of each changed file ([`CODEOWNERS`](../.github/CODEOWNERS)). New commits dismiss old approvals; conversations must be resolved | The owner, whose own pull requests need only green checks (GitHub doesn't let anyone approve their own) |
| **Release tags stay put** (`v*`) | A published version can't be moved or deleted | The owner |

A check that only warns gets ignored, so none of these does: a problem is fixed in the change that causes it.

**Renaming a CI job?** The first ruleset waits for the old name and blocks every pull request. Update the ruleset in
the same change.

**Workflow security (zizmor)** ([`zizmor.yml`](../.github/workflows/zizmor.yml)) reads the workflow files for mistakes
CodeQL doesn't look for, such as an action not pinned to a commit or a token with more permission than a job needs. A
finding fails the run. Fix it in the change that causes it. If a finding is on purpose (a `pull_request_target`
workflow that never checks out the pull request, say), mark that line `# zizmor: ignore[rule]` and write the reason
next to it.

**Workflow syntax (actionlint)** ([`actionlint.yml`](../.github/workflows/actionlint.yml)) checks that the workflow
files are valid: a misspelled expression, a `needs:` that names no job, a `run:` script that shellcheck flags. A finding
fails the run, so fix it in the change that causes it. actionlint isn't a GitHub action, so the workflow downloads one
pinned release with `gh` and stops unless the archive matches the SHA-256 written in the file. Dependabot can't see that
pin: to move it, change `VERSION` and `SHA256` together, taking the checksum from the release's
`actionlint_<version>_checksums.txt`. It can't check the inputs of an action pinned to a commit.

### Dependency files

`requirements*.txt` and `website/package*.json` have no code owner, so Dependabot's own approval is enough to merge
its minor and patch updates. [`dependency-guard.yml`](../.github/workflows/dependency-guard.yml) makes that safe: on
every pull request it posts a status called **Dependency files**, which fails when anyone but Dependabot or the owner
changed one of those files. A new dependency comes through an issue and the owner, never inside another change.
The short lists those files are built from, `tools/deps/*.in` ([Requirement hashes](#requirement-hashes)), do have an
owner, and the guard watches the folder too: choosing a package needs the owner's approval, and the check fails for
anyone else who changes one.

The guard runs from `main` and never checks out the pull request, so the pull request can't change what it checks. It
posts the status through the API on the pull request's last commit, because a check from `pull_request_target` isn't
attached to that commit, and that also means a change to the guard can't be tried on its own pull request: it takes
effect once it has merged. A pull request that was open before the guard existed gets its status from *Actions >
Dependency guard > Run workflow* (give it the pull request's number), or when it is next pushed to.

Also set: squash merging only (a pull request is one commit on `main`), branches deleted after merging, auto-merge
allowed, workflows get a read-only token unless they ask for more, and every outside contributor's workflow runs wait
for **Approve and run workflows** (*Settings > Actions > General*, "Require approval for all external contributors").

## Triage, once a week

New issues have the `needs triage` label. For each one, add its area (`acapella`, `spotify`, `library`,
`tutorials`, `install`), then do one of these and remove `needs triage`:

- scope it and add `help wanted`, or `good first issue` if it's small and well explained;
- assign whoever will do it;
- ask a question;
- close it kindly, with the reason (`duplicate`, `wontfix`).

Ideas stay open for votes. When one is chosen, write what's in and out of scope in the issue, then add `help wanted`.

## Review and merge

- Review against the definition of done in [AGENTS.md](../AGENTS.md). For a change people will see, look at the
  screenshots in both themes.
- Approve, then **Squash and merge**, or turn on **auto-merge** to merge as soon as CI passes.
- An outside contributor's CI waits for **Approve and run workflows**, every time. Audit the change first, as below,
  and again after each push.
- Your own pull request: the owner can merge once CI is green; any other maintainer needs another code owner's approval.

When a pull request says `Fixes #N` and issue N isn't assigned to its author, [`pr-assignment.yml`](../.github/workflows/pr-assignment.yml)
leaves one comment asking them to comment on the issue and wait (step 3 in [CONTRIBUTING.md](../CONTRIBUTING.md)). It
skips maintainers, Dependabot and Copilot, and never closes, labels or blocks anything, so step 1 of the audit below is
still yours. It runs on `pull_request_target`, which gives it a token that can write to pull requests from forks, so it
never checks out the pull request: it fetches its script from `main` (a test enforces this). To try it on an existing
pull request, run *Pull request assignment* from the Actions tab and enter the number; it comments for real, once.

A pull request that names no issue gets one comment too, asking which issue it is for (step 1), unless every file it
changes is a Markdown file or under `docs/`: the check can't tell a typo from a larger docs change. The comment has its
own marker, so it and the one above don't stop each other, and the same people are skipped. To decide, the check reads
the list of changed files through the GitHub CLI, never the files themselves.

### Auditing an outside pull request

The same steps for a person, a brand-new account or an AI agent, because none of them depends on trust. An agent does
them too and reports to the owner. It never approves or merges ([AGENTS.md](../AGENTS.md)).

1. **One issue.** The pull request says `Fixes #N`, issue N is assigned to its author, and everything in it serves that
   issue. Anything else, even a good fix, becomes its own issue.
2. **The author.** How old the account is, what else it has done, whether the description matches the code. A new
   account changes how closely you read, never whether you do.
3. **The files.** List all of them and read these twice: dependency files (`requirements*.txt`,
   `website/package*.json`), `.github/` (workflows, `CODEOWNERS`, Dependabot), `packaging/`, `tools/`,
   `tests/conftest.py`, `main.py`, and any binary, minified or encoded file, submodule or symlink.
4. **Every line.** Look for new URLs, network calls, `subprocess`, `eval`, `exec`, `pickle`, anything that reads
   `settings.json`, Spotify tokens or `.env`, and in a workflow `pull_request_target`, `secrets.` or a download piped
   into a shell. For an image, check it is the image the change needs and nothing else.
5. **Accidental edits.** Deleted text, reformatting, regenerated files: ask for them to be put back.
6. **Dependencies.** A new one never rides along with another change: ask for an issue first. Check the package: its
   exact name (a typo of a popular one?), publisher, first release date, source repository, install-time scripts,
   licence, and why nothing we already have will do. The owner decides. The answers go in a row of
   [dependencies.md](dependencies.md), and a test fails until the package has one.
7. **Run it in the right place.** CI is the sandbox. Don't run a pull request on a machine that holds credentials; if
   you must, use a throwaway container with no tokens, after reading the diff.
8. **Report, then approve.** Tell the owner what you found and your verdict. Start CI only after the audit, and approve
   only once CI is green and the owner agrees.

## Dependencies

Dependabot checks every Monday. It waits a few days before proposing a new release (a cooldown), so a broken or
hijacked version has time to be caught. Security fixes don't wait.

- **Minor and patch updates** arrive as one pull request per ecosystem (Python, the website, Actions).
  [`dependabot-auto-merge.yml`](../.github/workflows/dependabot-auto-merge.yml) approves them and turns on
  auto-merge, so they merge once CI is green. Nothing to do unless CI fails. A Python update that needs a package the
  requirements files don't list yet fails with *Hashes are required*: see [Requirement hashes](#requirement-hashes).
- **Major updates** arrive one per pull request, labelled `major update`, and wait. On the last day of each month,
  [`major-updates.yml`](../.github/workflows/major-updates.yml) opens an issue for each one and assigns it to
  Copilot, which reads the migration guide and opens a pull request. Copilot is an AI agent that reads pages from the
  web, so its pull request is audited like any other (above). Read it, click **Approve and run workflows** (and
  **Ready for review** if it's still a draft), then approve and merge it yourself once CI is green. Nothing it
  writes merges on its own. Dependabot then closes its own pull request.
- **Can't wait for the month to end** (a security fix in a major version)? Run *Major updates* from the Actions tab.

Every action in `.github/workflows/` is pinned to a full commit SHA, with its version in a trailing comment
(`uses: actions/checkout@<sha> # v7.0.1`), because a tag can be moved to other code and a commit can't. A test fails
on any that isn't. Dependabot's `github-actions` updates move the SHA and the comment together, so the pins stay
current; keep the comment in the `# vX.Y.Z` form.

The commit hooks in [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) are pinned the same way, as
`rev: <sha> # frozen: vX.Y.Z`, and a test fails on any `rev:` that isn't. Dependabot isn't set up for them, so nothing
proposes an update: look when you bump `ruff` in `requirements-dev.txt`, which the `ruff-pre-commit` version has to
match, and now and then otherwise. To update one, run `.venv/bin/pre-commit autoupdate --freeze` (it downloads each hook
repository, so read the diff afterwards), or find the commit by hand and write both the SHA and the version:

```
gh api repos/astral-sh/ruff-pre-commit/git/ref/tags/vX.Y.Z --jq .object
```

If `type` is `tag`, run `gh api repos/astral-sh/ruff-pre-commit/git/tags/<sha> --jq .object.sha` to get the commit.

### Requirement hashes

`requirements.txt`, `requirements-dev.txt` and `requirements-build.txt` pin every package they install, the ones nobody
chose included, to one version and to a hash of each file of that version. CI, the release and Copilot's setup install
with `pip install --require-hashes`, which stops when a package has no hash or a downloaded file doesn't match. A
tampered download, or an index that serves another file under the same version, fails the run instead of reaching a
build. (A plain `pip install -r` on your own machine checks the hashes too.) The same installs add `--only-binary :all:`:
pip then refuses to build a package from source, which would run that package's own build code on the runner. Every
package has a ready-made wheel for the systems CI and the release use (Windows x64, macOS arm64 and Linux x86_64), so
this only ever fails when a new version has none: the run says which package, and a person decides what to do.

`uv pip compile` writes the three files from the short lists in `tools/deps/` (`app.in`, `dev.in`, `build.in`: the
packages someone chose, by name), and each file's header records the command. Each file is complete in itself and
covers Windows, macOS and Linux: a package for one system only carries its marker (`; sys_platform == 'win32'`), and
every package has the hash of every file of that version, because we can't know which wheel a machine will pick.
The lists live in `tools/deps/` on purpose: Dependabot treats a `requirements*.in` file in the root as pip-compile's
input and would rebuild the `.txt` beside it with pip-compile, on Linux, without the Windows and macOS packages.

**Dependabot keeps the files current.** It changes a version and its hashes together, and a minor or patch update
still merges once CI is green. It doesn't work out dependencies: when a new
version needs a package the files don't list, or no longer needs one, the pull request fails with *Hashes are required
in --require-hashes mode* and you regenerate (below) on its branch.

**Regenerate** from the repository root, in this order, with [uv](https://docs.astral.sh/uv/) (a maintainer's tool, not
a dependency of the project). `--no-build` makes uv read package metadata and never build anything:

```
uv pip compile tools/deps/app.in --universal --python-version 3.12 --generate-hashes --no-build -o requirements.txt
uv pip compile tools/deps/dev.in -c requirements.txt --universal --python-version 3.12 --generate-hashes --no-build -o requirements-dev.txt
uv pip compile tools/deps/build.in -c requirements.txt --universal --python-version 3.12 --generate-hashes --no-build -o requirements-build.txt
```

Versions and hashes already in a file stay as they are, so this only adds what is missing and drops what nothing needs
any more. Then give each new package its row in [dependencies.md](dependencies.md). To move a package to a newer
version yourself, add `--upgrade-package <name>` to the command for the file that lists it first (`requirements.txt`
for anything the app needs, otherwise the dev or build one), then run the others as written. For a package that is new
to the files, uv picks the newest version: read its date, the cooldown above doesn't apply. Never paste in the hashes
pip prints when it refuses a package: they only say what happened to download.

**Check the hashes yourself** (bash or zsh; for the other two files, swap `app.in` and `requirements.txt` for `dev.in`
and `requirements-dev.txt`, then for `build.in` and `requirements-build.txt`). It asks PyPI for the hashes again and
prints nothing when the file has exactly those:

```
diff <(grep -v '^ *#' requirements.txt) <(uv pip compile tools/deps/app.in -c requirements.txt --universal --python-version 3.12 --generate-hashes --no-build --no-annotate --no-header 2>/dev/null)
```

### One-time setup: let the workflow assign Copilot

GitHub lets only a person assign Copilot, so the workflow needs the owner's token. Until it has one, the monthly
issues still open, labelled `help wanted`, and you can pick Copilot in each issue's **Assignees** menu.

1. Create a [fine-grained personal access token](https://github.com/settings/personal-access-tokens/new) for this
   repository only, with read and write access to **Actions**, **Contents**, **Issues** and **Pull requests**.
2. Add it as a repository secret named `COPILOT_TOKEN` (*Settings > Secrets and variables > Actions*).
3. Set a reminder for when it expires.

Copilot's pull requests wait for **Approve and run workflows** by default (*Settings > Copilot > Cloud agent*).
Leave it on: it's your look at what Copilot wrote before CI runs it.

## Security

What's switched on is listed in [SECURITY.md](../SECURITY.md). Alerts arrive in the **Security** tab and by email;
a private vulnerability report should get a reply within a week.

[OpenSSF Scorecard](https://scorecard.dev) scores the repository's supply-chain habits from 0 to 10 (protected
branches, pinned dependencies, read-only tokens, tests in CI). [`scorecard.yml`](../.github/workflows/scorecard.yml)
runs it on every push to `main` and once a week; to run it now, use *Run workflow* on **Scorecard** in the Actions tab.
The score is the badge at the top of the README. The
[full report](https://scorecard.dev/viewer/?uri=github.com/tomgreef/dj-toolkit) says what to fix first, and the
findings are also under *Security > Code scanning*. Each one worth fixing becomes its own issue. The workflow uses the
one third-party action here, `ossf/scorecard-action`, pinned to a commit. Scorecard only accepts results from a
workflow with a single job and no top-level `env`, so leave that layout as it is.

## Releasing

A release is a pull request that bumps the version: [releasing.md](releasing.md).
