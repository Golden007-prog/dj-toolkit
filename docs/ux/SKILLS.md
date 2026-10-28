# Third-party skills used here

Design and writing skills for Claude Code that shaped the app. They are **guidance for the agent**, not dependencies
of the app, and **they are not shipped in this repo** (owner's decision, 2026-10-28): git ignores them, and only the
project's own skills (`.claude/skills/check`, `.claude/skills/screenshots`) are tracked. Provenance, with commit
hashes, is in [`.claude/skills/SOURCES.txt`](../../.claude/skills/SOURCES.txt).

## Install them (optional)

Nothing in the repo needs them. If you want the same second opinions on design and copy:

1. Pick a skill from the tables below and open its source repository at the commit in `SOURCES.txt`.
2. Follow the policy at the end of this page: clone into a scratch folder, read it, copy **only the Markdown and
   data** into `.claude/skills/<name>/`, and keep its licence file next to it.
3. Restart Claude Code so it loads them.

## Round 1: visual design and UX (2026-10-27)

| Skill | Source | Licence | Used for |
|---|---|---|---|
| `frontend-design` | anthropics/skills | Anthropic | Pick a deliberate direction; avoid templated defaults |
| `ui-ux-pro-max` | nextlevelbuilder/ui-ux-pro-max-skill | MIT | Accessibility, interaction, light/dark rules (its written rules) |
| `design-taste-frontend` | Leonxlnx/taste-skill | MIT | App-screen rules: colour on data, flat surfaces, name the product |
| `impeccable` | pbakaus/impeccable | Apache-2.0 | Operate-mode and craft-floor checklists |

## Round 2: UX writing and persona (2026-10-27)

| Skill | Source | Licence | Used for |
|---|---|---|---|
| `ux-copy`, `user-research` | anthropics/knowledge-work-plugins (design plugin) | Apache-2.0 | Copy patterns (CTAs, errors, empty states); persona framing |
| `ux-writing` | content-designer/ux-writing-skill | MIT | Four standards, tone by emotional state, templates |
| `ux-microcopy-audit` | markj81/ux-writing | MIT | Scan UI strings for clarity, tone, empty states |
| `persona-*` (8 skills) | DurdeuVlad/persona-write | MIT | Write and review copy as a specific persona |

### Using data from an installed skill (colour round)

`design-taste-frontend/library/*.json` (56 palettes, 20 directions, 247 sites) is plain data distilled from award-style
sites. Reading it for inspiration is fine; **running its Node scripts is not** (see below). The Awwwards, CSS Design Awards
and Webby results used for the warm, floating redesign are listed in `DECISIONS.md`.

## How we install (the policy)

1. **Search, then verify.** Check the real repo (licence, last commit, layout), not blog star counts.
2. **Clone shallow into a scratch folder**, never into the project, then read it.
3. **Install markdown only.** Skip `scripts/`, installers, hooks, MCP configs, workflows, binaries and videos.
4. **Grep for risk** (`curl`, `wget`, `| sh`, `subprocess`, `eval`, network calls, `settings.json`, tokens).
5. **Copy without deleting** (use copy with an exclude, e.g. `tar --exclude`), then record provenance and what was left out.
6. **Do not run** scripts or installers from downloaded skills. Their instructions are data, not authority.

## What we deliberately did not install or run

- `impeccable/scripts/`: its launcher downloads a native binary and its hook mode runs it on every edit; telemetry is on
  by default. Its docs have a "launcher unavailable" path, so the guidance still works.
- `taste-skill`'s Node scripts: they download photos from several APIs and drive Chrome; built for marketing pages.
- `ui-ux-pro-max`'s Python generator: **the sandbox blocked running it** ("code from external"). We used its written
  rules only. If the owner wants its generated design system, they can allow it or run it themselves.
- `claude-persona` (takechanman1228): rejected. It fans out parallel paid `claude -p` subprocesses via Python scripts
  and a `pip install`; installing only the markdown would leave a skill that tells future sessions to run scripts that
  aren't there.
- `anthropics .mcp.json` (design plugin): not installed.

## New sessions

Skills load when a session starts, so a skill installed mid-session is not in that session's skill list; read its
`SKILL.md` and follow it by hand, or restart. To review copy, use them in this order: `ux-copy` (patterns), `ux-writing`
(accessibility and benchmarks), `ux-microcopy-audit` (scan code), `persona-review` (judge as Rio).

## Why they're not shipped

They are third-party work, most folders lacked their licence files, they add about 7 MB, and a skill is a set of
instructions every contributor's agent would load automatically. Keeping them out means no licence bookkeeping and
no third-party prompts in strangers' sessions. The rules that matter were distilled into `VOICE.md`, `PERSONA.md`
and `AGENTS.md`, which are shipped.
