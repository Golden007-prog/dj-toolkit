# Roadmap

Where things stand, and what would help most. The ideas themselves, with their votes, are the
[issues labelled `idea`](https://github.com/tomgreef/dj-toolkit/issues?q=is%3Aissue+is%3Aopen+label%3Aidea+sort%3Areactions-%2B1-desc).
Open an issue before starting anything big, so two people don't build the same thing.

## Status

| Area | State |
|---|---|
| Acapella prep | Works end to end. Tested with synthetic audio and a real audio-device handshake; **not yet with real acapellas by ear**. |
| Spotify sync | Ported from the owner's TypeScript tool and unit-tested; the matcher gave identical results on 1,000 real tracks. **Not yet run against a live Spotify app.** |
| Tutorials | Drafts. The rekordbox steps are unverified. Posts stay on your computer for now. |
| Persona and voice | An assumption, not research ([PERSONA.md](ux/PERSONA.md) lists the questions to ask DJs). |
| Install | Downloads for Windows and macOS (Apple silicon) from GitHub Releases, unsigned for now. See [releasing.md](releasing.md). |
| Requests | Ideas are GitHub issues labelled `idea`; a thumbs-up is a vote. The app and the website list the most-voted. |

## Good first issues

- **Reword the activity log.** A few Spotify messages say "cached", "dry run" or "authorize". They're listed in
  `KNOWN_COPY_DEBT` in `tests/test_guardrails.py`; fix one, delete its entry. ([VOICE.md](ux/VOICE.md))
- **A setting for the Spotify callback port.** The "port is busy" message tells people to change it, but only
  `settings.json` can.
- **Real setup screenshots.** Save real Spotify dashboard screenshots as `assets/setup/real/step1.png` … `step6.png`;
  the guide prefers them over the drawn ones.
- **Check a tutorial** against rekordbox and your CDJs or XDJs, and fix what's wrong in `assets/tutorials/tutorials.json`.

## Bigger pieces

- **Try it with real acapellas, by ear.** Report where the suggestion lands, and whether the tap timing feels late
  (it assumes a fixed 50 ms output delay that may need calibrating).
- **Signed downloads**, so Windows and macOS stop warning on first open (needs paid certificates), and an Intel Mac build.
- **A shared, anonymous forum** for the tutorials, behind the existing `Forum` interface in `djtoolkit/tutorials.py`.
- **Interview a few working DJs** with the questions at the end of [PERSONA.md](ux/PERSONA.md), and update it.

## How the project runs

Work on the repository itself, the things mature open-source projects do: issues labelled
[`security`](https://github.com/tomgreef/dj-toolkit/issues?q=is%3Aissue+is%3Aopen+label%3Asecurity),
[`ci`](https://github.com/tomgreef/dj-toolkit/issues?q=is%3Aissue+is%3Aopen+label%3Aci) and
[`community`](https://github.com/tomgreef/dj-toolkit/issues?q=is%3Aissue+is%3Aopen+label%3Acommunity).
Many are small and well explained, good for a first change.

## Ideas, not yet decided

Hearing the start marker while you scratch; snapping markers to onsets as you drag. The rest of the ideas are issues
labelled `idea`: vote for the ones you want, or add your own.
