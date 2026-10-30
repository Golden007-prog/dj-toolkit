# Changelog

Changes people would notice, newest first. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/). Each release's section becomes its release notes.

## [Unreleased]

### Added

- You can change the Spotify callback port (Spotify sync, More, Callback port) if something else uses 8888.
- You can now check a download. GitHub keeps a signed record of where each file was built, and the release has a
  `SHA256SUMS.txt` to check it arrived whole. How:
  [Check a download](https://github.com/tomgreef/dj-toolkit/blob/main/docs/releasing.md#check-a-download).
- Each release now has a list of the libraries inside the app, one for Windows and one for Mac (a software bill of
  materials), so a company or a security scanner can see what the download is made of. It says what it leaves out in
  [Check a download](https://github.com/tomgreef/dj-toolkit/blob/main/docs/releasing.md#check-a-download).

## [0.1.1] - 2026-10-29

### Changed

- The repository is now `tomgreef/dj-toolkit`, to match the name of the app, and the website moved to
  `tomgreef.github.io/dj-toolkit/`. Old repository links redirect; the old website address doesn't.

### Fixed

- The Requests page loads the most-voted ideas again. Version 0.1.0 looked them up under the repository's old name and
  can't find them, so update to this version.
- On macOS, Open the unmatched report (Spotify sync, More) now opens the report. It only worked on Windows.

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
