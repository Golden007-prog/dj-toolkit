# Changelog

Changes people would notice, newest first. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions will follow [Semantic Versioning](https://semver.org/) once there are releases.

## [Unreleased]

### Added

- Open-source setup: MIT licence, contributor guide, code of conduct, security policy, issue and pull request
  templates, and CI on Windows.
- A harness for AI-assisted work: `AGENTS.md`, one command that checks everything (`tools/check.py`), real-window
  screenshots in both themes (`tools/screenshots.py`), and guardrail tests that turn the project's written rules
  into checks.
- A landing page in `website/` (Astro), published with GitHub Pages.

### Changed

- The code is formatted with ruff, and dependencies are pinned to the versions the tests pass with.
- The music folder field's example no longer shows a personal folder name.

## Before the open-source release

Acapella prep (lock four beats, set the start, playhead, loop, click, scratch, export with a count-in and the BPM
tagged), Spotify sync (a port of the owner's TypeScript tool, with a guided setup), tutorials with an anonymous local
Q&A, and the Booth and Daylight looks with an accent picker. The reasoning is in
[docs/ux/DECISIONS.md](docs/ux/DECISIONS.md).
