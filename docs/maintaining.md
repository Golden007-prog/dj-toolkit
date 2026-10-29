# Maintaining

For maintainers and the owner: what GitHub enforces, and the routine jobs. Who can do what, and how people join:
[GOVERNANCE.md](../GOVERNANCE.md).

## What GitHub enforces

Three rulesets (*Settings > Rules > Rulesets*):

| Ruleset | What it does | Who can skip it |
|---|---|---|
| **Checks must pass** (`main`) | Nothing lands until these are green: `App on windows-latest (lint, format, tests)`, `App on macos-latest (lint, format, tests)`, `Website (build)` and `Dependency review`. No force pushes, and `main` can't be deleted | Nobody |
| **A code owner approves** (`main`) | Changes arrive by pull request, with an approval from a code owner of each changed file ([`CODEOWNERS`](../.github/CODEOWNERS)). New commits dismiss old approvals; conversations must be resolved | The owner, whose own pull requests need only green checks (GitHub doesn't let anyone approve their own) |
| **Release tags stay put** (`v*`) | A published version can't be moved or deleted | The owner |

**Renaming a CI job?** The first ruleset waits for the old name and blocks every pull request. Update the ruleset in
the same change.

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
   licence, and why nothing we already have will do. The owner decides.
7. **Run it in the right place.** CI is the sandbox. Don't run a pull request on a machine that holds credentials; if
   you must, use a throwaway container with no tokens, after reading the diff.
8. **Report, then approve.** Tell the owner what you found and your verdict. Start CI only after the audit, and approve
   only once CI is green and the owner agrees.

## Dependencies

Dependabot checks every Monday. It waits a few days before proposing a new release (a cooldown), so a broken or
hijacked version has time to be caught. Security fixes don't wait.

- **Minor and patch updates** arrive as one pull request per ecosystem (Python, the website, Actions).
  [`dependabot-auto-merge.yml`](../.github/workflows/dependabot-auto-merge.yml) approves them and turns on
  auto-merge, so they merge once CI is green. Nothing to do unless CI fails.
- **Major updates** arrive one per pull request, labelled `major update`, and wait. On the last day of each month,
  [`major-updates.yml`](../.github/workflows/major-updates.yml) opens an issue for each one and assigns it to
  Copilot, which reads the migration guide and opens a pull request. Copilot is an AI agent that reads pages from the
  web, so its pull request is audited like any other (above). Read it, click **Approve and run workflows** (and
  **Ready for review** if it's still a draft), then approve and merge it yourself once CI is green. Nothing it
  writes merges on its own. Dependabot then closes its own pull request.
- **Can't wait for the month to end** (a security fix in a major version)? Run *Major updates* from the Actions tab.

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

## Releasing

A release is a pull request that bumps the version: [releasing.md](releasing.md).
