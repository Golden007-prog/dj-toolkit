# Testing

```bat
check.bat                                            :: everything CI runs: lint, format, all tests
check.bat --fix                                      :: let ruff fix what it can first
.venv\Scripts\python -m pytest tests\test_audio.py   :: one file
.venv\Scripts\python -m pytest -k "start and grid"   :: tests whose names match
```

About 170 tests, about a minute. No sound card, never your real settings, and never the network:
`tests/conftest.py` points the app folder at a temporary one, makes any real web request fail, and runs Qt without
a window. The built app has a check of its own, `--self-test` (see [releasing.md](releasing.md)).

## What is covered

| File | Covers |
|---|---|
| `test_acapella_flow.py` | The two-step workflow end to end, the way a user clicks, on synthetic audio |
| `test_alignment.py` | The grid fit, the beat suggestion, onset refinement, the transport (play, loop, scrub, click) |
| `test_audio.py` | Count-in length and placement, tempo detection, export and BPM tags |
| `test_waveform.py` | Zoom, pan, markers, dragging, keyboard, painting every state |
| `test_spotify.py` | Matching, scoring, search limits, the playlist diff, scanning, importing the old tool's files |
| `test_settings_memory.py` | Remembered folders and per-file work, and their fallbacks |
| `test_ui_logic.py` | Preview before sync, dialogs, the setup guide, tutorials, window state, looks and accents |
| `test_theme.py` | Contrast of every colour pair in every mode and accent |
| `test_feedback.py` | The most-voted ideas, the pre-filled GitHub forms, the Requests page, and that tests can't use the network |
| `test_guardrails.py` | The project's rules, as checks (below) |

## Writing a test

- **Act like the user.** Drive the real widget: `tab = AcapellaTab(Settings(), audio=False)`, `tab.install(...)`,
  `tab.add_beat(...)`, then assert on what the user would see (`tab.status.text()`, the exported file).
- **Make the audio.** `_track()` in `test_acapella_flow.py` builds a click track with a louder "chorus"; reuse the
  idea rather than adding audio files.
- **Fake the network.** Spotify tests use a stand-in client with canned results; nothing calls Spotify.
- **Name it as a sentence** about behaviour: `test_a_changed_file_does_not_reuse_old_alignment`.

## Guardrails

`tests/test_guardrails.py` turns the rules in [AGENTS.md](../AGENTS.md) into checks, so a person or an agent who
breaks one finds out in seconds. Each failure says what to do instead.

| Check | Fails when |
|---|---|
| Layers | `audio/`, `spotify/`, `settings.py` or `tutorials.py` import Qt or the UI |
| Theme colours | a hex colour appears in `djtoolkit/ui/` outside `theme.py` |
| File dialogs | `QFileDialog` is used outside `ui/dialogs.py` |
| Qt traps | `setButtonSymbols(NoButtons)`, `setGraphicsEffect`, `a << b + c`, the `offscreen` platform in `tools/` |
| Voice | user-facing text uses a banned word, an exclamation mark or an emoji |
| Hygiene | secrets, `.env` or token files, personal paths, or files over 800 KB would be committed |
| Doc links | a relative link in a Markdown file points at nothing |

The voice check has a short list of older messages, `KNOWN_COPY_DEBT`, that predate it. The list only shrinks: fix a
message, delete its entry, and the test tells you if you forget. To change a rule, change its doc and its check in
the same pull request and explain why.

## Looking

Tests don't see clipped labels or muddy colours. After a UI change, run `tools\screenshots.py` and open the images in
`screenshots\`, Booth and Daylight. Attach them to your pull request.

## CI

GitHub Actions runs `tools/check.py` on Windows for every push and pull request, and builds the website on Linux
(`.github/workflows/ci.yml`). Pushing to `main` with changes in `website/` also publishes the site
(`.github/workflows/pages.yml`).
