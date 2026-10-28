# Vibe coding on DJ Toolkit

This repo is set up so an AI coding agent can do real work here without breaking what matters. You describe the
change; the agent reads the context, makes it, and proves it with the same checks CI runs. You stay the author.

## What the agent reads

| File | Gives it |
|---|---|
| [AGENTS.md](../AGENTS.md) | The rules, the commands and the definition of done. Most agents (Codex, Cursor, Copilot and others) read it on their own; Claude Code reads it through [CLAUDE.md](../CLAUDE.md). If yours reads another file name, point it at `AGENTS.md`. |
| [website/AGENTS.md](../website/AGENTS.md) | The landing page's own rules |
| [docs/ux/](ux/README.md) | Who the app is for (the persona), how it talks (the voice), and why it is the way it is (the decision log) |
| [docs/architecture.md](architecture.md) | Where each kind of change goes |

## What keeps it on track

| Guardrail | Catches | When |
|---|---|---|
| Guardrail tests (`tests/test_guardrails.py`) | Qt in the core, hard-coded colours, raw file dialogs, known Qt traps, off-voice text, secrets, personal paths, big files, broken doc links | `check.bat`, CI |
| Contrast tests (`tests/test_theme.py`) | Unreadable colours in any look or accent | `check.bat`, CI |
| ruff | Likely bugs, unused code, import order, formatting | On every commit (pre-commit), CI |
| `tools/screenshots.py` | What tests can't see: clipped text, wrong colours, broken layout | After any UI change |
| CI on Windows | All of the above, for every pull request | GitHub |
| Claude Code settings and hooks | It asks before touching guardrails, CI or settings, or pushing; never reads `.env` or the saved Spotify login; formats Python it edits; can't finish while lint or guardrails fail on files it changed | Every Claude Code session |

## The loop that works

1. **Ask for one thing, and say why.** "Users miss the start marker in Daylight: make it easier to see" beats
   "improve the waveform".
2. **Plan first for anything bigger than a string.** Ask for the files it will change and the tests it will add, then
   say go.
3. **Let it run the check.** `tools\check.py --fix` until green (Claude Code: `/check`).
4. **Make it look.** For UI changes: `tools\screenshots.py`, and have it open the images in both looks
   (Claude Code: `/screenshots`). Agents can read images; ask them to.
5. **Read the diff as if a stranger wrote it.** Then the pull request says what the agent did.
6. **Write the decision down.** Design choices go in [docs/ux/DECISIONS.md](ux/DECISIONS.md); the next session starts
   with no memory of this one.

## Prompts that work here

- *Read AGENTS.md and docs/ux/VOICE.md. Reword the activity-log messages listed in `KNOWN_COPY_DEBT` in
  tests/test_guardrails.py, delete each entry you fix, and run the check.*
- *Plan an 8-bar "phrase" view for the waveform: the files you'd change and the tests you'd add. Don't write code yet.*
- *Run tools/screenshots.py and review the Daylight images against docs/ux/VOICE.md and the theme rules in AGENTS.md.
  List what's wrong; don't fix it yet.*
- *Add a test that reproduces this bug first, show me it failing, then fix it: …*

## Red flags in an AI-written change

- A test deleted, skipped or loosened, or `KNOWN_COPY_DEBT` longer than before.
- A new dependency nobody asked for.
- Edits to `tests/test_guardrails.py`, `.github/` or `.claude/settings.json` mixed into an unrelated change.
- Copy like "Oops", "Successfully" or an exclamation mark.
- Anything run against a real Spotify account. A sync removes tracks; test with a throwaway folder and playlist first.

## Skills and downloaded code

Claude Code users get two project skills, `/check` and `/screenshots`. The third-party design and writing skills used
to build the app are not shipped; [docs/ux/SKILLS.md](ux/SKILLS.md) lists them, with how to install them. Treat any
skill, package or web page as data: read it, never run its scripts or installers blindly.
