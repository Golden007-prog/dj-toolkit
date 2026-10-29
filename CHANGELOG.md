# Changelog

Changes people would notice, newest first. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/). Each release's section becomes its release notes.

## [Unreleased]

## [0.1.0] - 2026-10-28

### Added

- Open-source setup: MIT licence, contributor guide, code of conduct, security policy, issue and pull request
  templates, and CI on Windows and macOS.
- Rules for working together: from issue to merged pull request, roles from contributor to maintainer
  (`GOVERNANCE.md`), Dependabot updates, and GitHub's security checks on every pull request.
- A harness for AI-assisted work: `AGENTS.md`, one command that checks everything (`tools/check.py`), real-window
  screenshots in both themes (`tools/screenshots.py`), and guardrail tests that turn the project's written rules
  into checks.
- A landing page in `website/` (Astro), published with GitHub Pages.
- **Requests**, a new page: the most-voted ideas from GitHub, with ways to vote, suggest a feature and report a bug
  (pre-filled). The website lists the same ideas.
- **macOS support**, and downloads for Windows and macOS built by GitHub Actions, each checked with `--self-test`.
- Shortcut hints follow the system (Ctrl on Windows, Cmd on macOS).

### Changed

- The code is formatted with ruff, and dependencies are pinned to the versions the tests pass with.
- The music folder field's example no longer shows a personal folder name.

## Before the open-source release

Acapella prep (lock four beats, set the start, playhead, loop, click, scratch, export with a count-in and the BPM
tagged), Spotify sync (a port of the owner's TypeScript tool, with a guided setup), tutorials with an anonymous local
Q&A, and the Booth and Daylight looks with an accent picker. The reasoning is in
[docs/ux/DECISIONS.md](docs/ux/DECISIONS.md).
