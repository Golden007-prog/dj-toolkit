# Roadmap

Where things stand, and what would help most. Open an issue before starting anything big, so two people don't
build the same thing.

## Status

| Area | State |
|---|---|
| Acapella prep | Works end to end. Tested with synthetic audio and a real audio-device handshake; **not yet with real acapellas by ear**. |
| Spotify sync | Ported from the owner's TypeScript tool and unit-tested; the matcher gave identical results on 1,000 real tracks. **Not yet run against a live Spotify app.** |
| Tutorials | Drafts. The rekordbox steps are unverified. Posts stay on your computer for now. |
| Persona and voice | An assumption, not research ([PERSONA.md](ux/PERSONA.md) lists the questions to ask DJs). |
| Install | From source only. No installer yet. |

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
- **A Windows installer** with PyInstaller. `djtoolkit/paths.py` already finds assets inside a bundle.
- **A shared, anonymous forum** for the tutorials, behind the existing `Forum` interface in `djtoolkit/tutorials.py`.
- **Interview a few working DJs** with the questions at the end of [PERSONA.md](ux/PERSONA.md), and update it.

## Ideas, not yet decided

Hearing the start marker while you scratch; snapping markers to onsets as you drag; an 8- or 16-bar phrase view;
time-stretching to a target BPM; batch mode for a folder of acapellas; macOS support.
