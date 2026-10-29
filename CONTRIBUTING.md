# Contributing

Thanks for helping. DJ Toolkit is small, so a good change is small too.

## Ways to help

- **Vote on what comes next.** Every idea is an issue labelled
  [`idea`](https://github.com/tomgreef/dj-toolkit/issues?q=is%3Aissue+is%3Aopen+label%3Aidea+sort%3Areactions-%2B1-desc),
  and a thumbs-up reaction is a vote (please don't comment "+1"). The website and the app's Requests page list the
  most-voted ones. You can suggest an idea or report a bug from either, too.
- **Ask a question, or talk DJ.** [Discussions](https://github.com/tomgreef/dj-toolkit/discussions) has Q&A,
  *Show and tell* for your sets and workflow, and *DJ talk*. An issue is for something to do; a question goes there.
- **DJ feedback, no code needed.** Try it on a real acapella or your own folders, and tell us what felt off.
  Open an issue and pick *DJ feedback*.
- **Argue with the drafts.** The tutorials and the persona ([docs/ux/PERSONA.md](docs/ux/PERSONA.md)) are guesses
  written to be challenged. "I'd do this differently, because…" is exactly what we want.
- **Fix or build something.** Start with an issue labelled `good first issue` or `help wanted`, or the
  [roadmap](docs/roadmap.md).

## From issue to merged pull request

1. **Start with an issue.** Pick a form at [New issue](https://github.com/tomgreef/dj-toolkit/issues/new/choose):
   bug, idea, DJ feedback, or a change to the code, tests or docs. A typo fix in the docs can skip this step; a pull
   request from outside that names no issue and changes more than the docs gets a comment asking which issue it is for.
2. **Triage.** A maintainer reads each new issue (label `needs triage`) within about a week, then labels it, asks a
   question, or closes it with a reason. Issues open to anyone get `help wanted` or `good first issue`.
3. **Claim it.** Comment that you'd like to take it and a maintainer assigns you. Nothing to show after two weeks?
   It's open to others again, no hard feelings.
4. **Build it** on a branch of your fork (`git switch -c fix/short-name`, or `feature/`, `docs/`), following
   [AGENTS.md](AGENTS.md): the rules and the definition of done, for people and AI agents alike. Changing anything
   a user sees or reads? Read [docs/ux/VOICE.md](docs/ux/VOICE.md) first, and afterwards run
   `.venv\Scripts\python tools\screenshots.py` and look at both themes. Run `check.bat --fix` until it passes.
5. **Open a pull request** that says `Fixes #123`, and fill in the template. Not finished yet? Open it as a draft
   to get early feedback.
6. **Review.** CI must pass, a code owner approves (see [GOVERNANCE.md](GOVERNANCE.md)), and every conversation is
   resolved. Expect a first review within a week. New commits need a fresh approval.
7. **Merge.** A maintainer squash-merges it: the pull request's title becomes the commit on `main`, and the issue
   closes.

## Set up (Windows, about five minutes)

```bat
git clone https://github.com/<you>/dj-toolkit.git
cd dj-toolkit
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\pre-commit install
check.bat
```

`check.bat` runs what CI runs: lint, format and about 180 tests (a minute, no network, no sound card).
On macOS, use `.venv/bin/python tools/check.py`. More detail, and fixes for common setup problems:
[docs/getting-started.md](docs/getting-started.md).

## What makes a pull request easy to merge

- One topic. Small pull requests get reviewed quickly.
- Tests that act like a user would (see `tests/test_acapella_flow.py`).
- A design decision gets a short entry in [docs/ux/DECISIONS.md](docs/ux/DECISIONS.md); a change users would notice
  gets a line in [CHANGELOG.md](CHANGELOG.md) under *Unreleased*.
- **AI-assisted is welcome.** You're still the author: read every line, run the check, and say in the pull request
  what the agent did. [docs/vibe-coding.md](docs/vibe-coding.md) has the workflow that works here.
- A title that's plain and imperative, under 72 characters, like `Snap the start marker to the grid`. It becomes
  the commit message.
- Every outside pull request waits for a maintainer to read it and start its CI, after each push. That's how we keep
  everyone's code and downloads safe, not a judgement of you. It's why a pull request that changes one thing is
  merged faster than one that changes five, and why a new dependency needs its own issue first.

## Grow with the project

Regular contributors become collaborators, and then maintainers of an area. [GOVERNANCE.md](GOVERNANCE.md) says how.

## Be kind, and report security problems privately

Everyone here follows the [code of conduct](CODE_OF_CONDUCT.md). Found a security problem? Don't open an issue;
see [SECURITY.md](SECURITY.md).

By contributing, you agree that your work is released under the [MIT licence](LICENSE).
