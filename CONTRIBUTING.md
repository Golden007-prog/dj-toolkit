# Contributing

Thanks for helping. DJ Toolkit is small, so a good change is small too.

## Ways to help

- **DJ feedback, no code needed.** Try it on a real acapella or your own folders, and tell us what felt off.
  Open an issue and pick *DJ feedback*.
- **Argue with the drafts.** The tutorials and the persona ([docs/ux/PERSONA.md](docs/ux/PERSONA.md)) are guesses
  written to be challenged. "I'd do this differently, because…" is exactly what we want.
- **Fix or build something.** Start with the [roadmap](docs/roadmap.md), or an issue labelled `good first issue`.

## Set up (Windows, about five minutes)

```bat
git clone https://github.com/<you>/on-the-one.git
cd on-the-one
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\pre-commit install
check.bat
```

`check.bat` runs what CI runs: lint, format and about 160 tests (a minute, no network, no sound card).
More detail, and fixes for common setup problems: [docs/getting-started.md](docs/getting-started.md).

## Make a change

1. Branch from `main`: `git switch -c fix/short-name`.
2. Read [AGENTS.md](AGENTS.md): the rules and the definition of done. It's written for AI agents and people alike.
3. Changing anything a user sees or reads? Read [docs/ux/VOICE.md](docs/ux/VOICE.md) first, and afterwards run
   `.venv\Scripts\python tools\screenshots.py` and look at both themes.
4. Run `check.bat --fix` until it passes.
5. Open a pull request and fill in the template. For UI changes, attach before and after screenshots.

## What makes a pull request easy to merge

- One topic. Small pull requests get reviewed quickly.
- Tests that act like a user would (see `tests/test_acapella_flow.py`).
- A design decision gets a short entry in [docs/ux/DECISIONS.md](docs/ux/DECISIONS.md); a change users would notice
  gets a line in [CHANGELOG.md](CHANGELOG.md) under *Unreleased*.
- **AI-assisted is welcome.** You're still the author: read every line, run the check, and say in the pull request
  what the agent did. [docs/vibe-coding.md](docs/vibe-coding.md) has the workflow that works here.
- Commit messages: plain and imperative, under 72 characters, like `Snap the start marker to the grid`.

## Be kind, and report security problems privately

Everyone here follows the [code of conduct](CODE_OF_CONDUCT.md). Found a security problem? Don't open an issue;
see [SECURITY.md](SECURITY.md).

By contributing, you agree that your work is released under the [MIT licence](LICENSE).
