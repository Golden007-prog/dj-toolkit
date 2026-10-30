<p align="center">
  <img src="website/public/screens/acapella-booth.webp" width="880"
       alt="DJ Toolkit's Acapella prep page: a vocal waveform with four numbered beat markers locked at 124 BPM">
</p>

# DJ Toolkit

[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/tomgreef/dj-toolkit/badge)](https://scorecard.dev/viewer/?uri=github.com/tomgreef/dj-toolkit)

Prep tools for working DJs. Free and open source, for Windows and macOS.

- **Acapella prep.** Lock the beat grid on four beats at the chorus, mark where the vocal comes in, and export it
  with a count-in. It lands on the downbeat, first time.
- **Spotify sync.** Each music folder becomes a Spotify playlist. You see every change before anything changes.
- **Tutorials.** Short, opinionated prep guides you can question, anonymously.
- **Requests.** Vote on what gets built next, suggest a feature or report a bug, right from the app.

Two looks: **Booth** for dark rooms and late-night prep, **Daylight** for a laptop in the sun.
See it, and try the four-beat lock, on the [website](https://tomgreef.github.io/dj-toolkit/).

> **Early days.** It's tested with generated audio and about 160 automated tests, but not yet with many real
> acapellas or a live Spotify account. Try it and [tell us what felt off](CONTRIBUTING.md#ways-to-help).

## Install

Download it from the [latest release](https://github.com/tomgreef/dj-toolkit/releases/latest). Nothing else to install.

**Windows 10 and 11:** unzip `DJ-Toolkit-Windows.zip`, open the folder and double-click **DJ Toolkit**.
If Windows says it protected your PC, choose **More info**, then **Run anyway**.

**macOS 12 or later (Apple silicon):** open `DJ-Toolkit-macOS.dmg` and drag DJ Toolkit into Applications.
If macOS says it can't check the app, open **System Settings > Privacy & Security** and choose **Open Anyway**.

The warnings appear because the app isn't signed with a paid certificate yet; all of its code is here, and you can
[check that a download was built from it](docs/releasing.md#check-a-download).
Your settings and your Spotify login stay on your computer, exports are saved as new files, and your music files are
never changed. How to use it: [docs/user-guide.md](docs/user-guide.md).
Prefer to run it from source? [docs/getting-started.md](docs/getting-started.md) takes about five minutes.

## Help build it

DJs, designers, writers and developers are all welcome, and AI-assisted work is too.

| I want to | Read |
|---|---|
| Ask a question, or talk DJ | [Discussions](https://github.com/tomgreef/dj-toolkit/discussions) |
| Vote on ideas, report a bug or make a first change | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Get it running for development | [docs/getting-started.md](docs/getting-started.md) |
| Understand how it fits together | [docs/architecture.md](docs/architecture.md) |
| Work with an AI coding agent | [docs/vibe-coding.md](docs/vibe-coding.md) (agents read [AGENTS.md](AGENTS.md)) |
| Know who it's for and how it talks | [docs/ux/](docs/ux/README.md) |
| Find something to build | [docs/roadmap.md](docs/roadmap.md) |
| Grow from first pull request to maintainer | [GOVERNANCE.md](GOVERNANCE.md) |

## Licence

[MIT](LICENSE). DJ Toolkit is an independent project, not affiliated with Spotify or AlphaTheta (rekordbox).
