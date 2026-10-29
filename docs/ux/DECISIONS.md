# Decisions and feedback log

Newest first. **Append here whenever the owner gives feedback or a design decision is made.** A future session
(or an open-source contributor) has no memory of the conversation; this file is the memory.
Format: what was asked → what we did → why → what is still open.

---

## 2026-10-29: Dependency files keep Dependabot's auto-merge, with a guard

**Owner request.** Close the gap that left `requirements*.txt` and `website/package*.json` without a code owner (#59),
but keep Dependabot's minor and patch updates merging themselves.

**What we did.** A workflow that runs from `main` posts a status, **Dependency files**, on every pull request. It
fails when anyone but Dependabot or the owner changed one of those files. It becomes a required check in the ruleset
only after it has run on a real pull request (`docs/maintaining.md`).

**Why this and not an owner for those files.** An owner would also have to approve Dependabot's pull requests, which
ends the auto-merge. A check written as part of a pull request can be edited by that pull request, so the guard uses
`pull_request_target`, never checks out the pull request, and reports through the commit status API. The cost is that
it can't be tested before it merges, and that it needs one ruleset change afterwards.

**Still open.** Dependabot's own pull requests are trusted as they are: a hijacked release is caught by the seven-day
cooldown and by CI, not by this guard.

---

## 2026-10-29: Every outside and AI-written change waits for the owner

**Owner request.** After a new account sent its first pull request: people, and the AI agents they use, might try to
sneak in something harmful, such as a dependency that steals data. Make rules so every change is inspected and the
owner controls all the work agents provide.

**What we did.** `AGENTS.md` says what an agent does with a pull request it didn't write: audit it, report, never
approve, merge or start CI, and never run it on a machine that holds credentials. `docs/maintaining.md` has the
checklist (one issue, the author, the files, every line, accidental edits, dependencies, where to run it, report then
approve). GitHub now holds the workflow runs of every outside contributor, not just first-timers (*Settings >
Actions > General*). Copilot's monthly major updates no longer turn on auto-merge: the owner reads and merges them.
`test_repo_rules.py` fails if any workflow other than Dependabot's minor and patch flow approves or merges a pull request.

**Why.** Copilot reads migration guides from the web, which an attacker can write, and the old flow merged what it
produced once CI was green, with the owner's token and no review. CI can't tell a harmless dependency from a harmful
one: `Dependency review` only knows about published vulnerabilities.

**Still open.** Dependabot's minor and patch updates still merge themselves once CI is green, after a seven-day
cooldown: the owner's call. The dependency files have no code owner, so a future second maintainer could approve a
change to them alone (#59). Python dependencies are pinned by version, not by hash (#60). A new dependency isn't yet
forced to come with a written reason (#61), and the website's install scripts still run (#62).

---

## 2026-10-29: The repository is called dj-toolkit

**Owner request.** The repository was `on-the-one` but everything a user sees says "DJ Toolkit". Rename the repository
to `dj-toolkit`, and change the code so everything keeps working.

**What we did.** The owner renamed the repository on GitHub. This change updates every mention of the old name: the
docs, the issue forms, the website's fallback links, the two workflows that only run on this repository, and the
repository name the app searches for ideas (`djtoolkit/feedback.py`). The product name, the Python package
(`djtoolkit`) and the data folder (`DJToolkit`) stay as they are.

**Why it needed care.** GitHub redirects the old repository, issue, clone and release-download links, but not two
things. GitHub Pages: the site must be deployed again under `tomgreef.github.io/dj-toolkit/`, and the old address
stops working. GitHub's search API: it answers 422 to `repo:tomgreef/on-the-one`, so the Requests page in version
0.1.0 can't load ideas. Only a new release fixes that.

**Open.** Publish the next release soon, for the Requests page. "On the one" is still the tagline and the idea behind
the project; only the repository's name changed.

---

## 2026-10-28: Who approves what, roles, Dependabot and security

**Owner request.** "I need to approve all PRs, otherwise this might go crazy", while letting developers grow from
contributor to maintainer. A clear path from issue to pull request, with templates. Dependabot with auto-merge for
minor and patch updates; major updates handed to Copilot at the end of the month to follow the migration guide, with
auto-merge once the checks pass. GitHub's security features, set up the way best practice says. And for agents: in
chat, only questions and results, no running commentary.

**Done.**
- **Approval:** `.github/CODEOWNERS` makes the owner the code owner of everything, and the ruleset *A code owner
  approves* requires their approval. The owner is exempt from that ruleset, because GitHub never lets anyone approve
  their own pull request. The ruleset *Checks must pass* has no exemptions: nothing lands with red CI, whoever wrote
  it. *Release tags stay put* stops a published version from being moved. Squash merging only.
- **Roles** (`GOVERNANCE.md`): contributor, collaborator (write access, invited after about three merged pull
  requests), maintainer (listed in `CODEOWNERS` for an area, so their approval counts), owner. A personal-account
  repository has only owner and collaborator levels; moving to a free organization adds Triage and Maintain roles.
- **Workflow** (`CONTRIBUTING.md`, `docs/maintaining.md`): every issue form adds `needs triage`, and a new form
  covers code, tests and docs. A maintainer triages weekly to `help wanted` or `good first issue`; you claim an issue
  by commenting; a pull request says `Fixes #N`.
- **Dependabot:** weekly, with a cooldown (new releases wait 3 to 14 days, against hijacked packages). Minor and patch
  updates come grouped and merge themselves: a workflow approves them. That approval counts only because the
  dependency files have no code owner. Majors get the label `major update`. On the last day of the month
  `major-updates.yml` opens an issue for each and assigns Copilot. When Copilot's pull request is ready, auto-merge
  turns on with the owner's token, so it follows the owner's rules and merges when green. GitHub only lets a person
  assign Copilot, so this needs a `COPILOT_TOKEN` secret; until the owner adds one, the issues wait for a person.
  Copilot's pull requests also need **Approve and run workflows**, GitHub's default. We kept it as the owner's look.
- **Releases** now publish themselves when a pull request that bumps `__version__` merges. Before, you pushed a tag
  by hand. The notes come from the version's CHANGELOG section.
- **Security:** private vulnerability reporting, Dependabot alerts, secret scanning with push protection, CodeQL
  (Python, the website, the workflows), dependency review on every pull request (blocks moderate or worse), and
  read-only workflow tokens by default.
- `tests/test_repo_rules.py` checks the parts that live in files: only the dependency files lack an owner, majors
  never merge themselves, and every issue form waits for triage.

**Found on the way.** The first macOS CI run caught a real bug. Exporting to a USB stick that isn't plugged in didn't
fall back on a Mac, because the drive check only knew Windows drive letters. `drive_of` now knows `/Volumes/<name>`.

**Open:** the owner creates `COPILOT_TOKEN` (`docs/maintaining.md` has the steps); a free organization once there are
more than two maintainers.

## 2026-10-28: Market research, issues, voting, and Windows and macOS downloads

**Owner request.** After publishing: research the market and create issues for features to build next; a voting system
so people can request features and report bugs from the desktop app, the website or GitHub; the app available on
Windows and macOS, with easy install steps.

**Market research (web, October 2026).** Library managers (Lexicon, about $17 a month) move cues and grids between DJ
apps. rekordbox 7, Serato, Traktor and VirtualDJ all have live stems, but blind tests rate their vocals unevenly and
prep guides recommend separating key tracks offline. Open-source tools (Trackmatch, InPhase, rdbs) match Spotify
playlists with local libraries; none links you to buy what's missing. USB exports keep failing DJs (a rekordbox
release was pulled in March 2026; a CDJ-3000 firmware lost playlists in October 2025). Mixed In Key ($58) leads key
detection; KeyFinder is the free option. Nothing found does count-in and grid prep for acapellas: that's our niche.
This became issues #1 to #11 (label `idea`), plus four good first issues (#12 to #15), two calls for real-world
testing (#16, #17) and the two pieces built here (#18, #19).

**Voting, done.** One list for everyone: GitHub issues labelled `idea`, a thumbs-up reaction is a vote. The app's new
**Requests** page (`ui/requests_tab.py`, data in `feedback.py`, no Qt there) shows the most-voted ideas, fetched only
when the page is opened, and opens GitHub's pre-filled forms in the browser to vote, suggest or report (the bug form
gets the app version and system). The website lists the same ideas, read when it's built and rebuilt daily.
**Why GitHub:** no backend to run or moderate, free, open, and the same list developers work from. **The cost:** voting
needs a free GitHub account, which many DJs don't have; that's said plainly wherever people vote. **Open:** a
no-account vote (a small backend, or votes counted from the app) if DJs ask for it.

**Windows and macOS, done.** The app folder follows the system (`settings.app_dir`: `%APPDATA%` on Windows,
`~/Library/Application Support` on macOS, `DJTOOLKIT_HOME` overrides for tests). Mac fonts (Helvetica Neue, DIN
Alternate) and native shortcut hints. PyInstaller builds both (`packaging/dj-toolkit.spec`); `main.py --self-test` proves
a build works (assets, tempo analysis with numba, MP3 export with ffmpeg, Qt) and runs in the release workflow on both
systems. The Windows build was built and self-tested locally (about 485 MB unpacked: numba's compiler and ffmpeg are
most of it); the macOS build is only checked in CI. **Not done:** code signing (first opens warn; the install steps
say how to continue), Intel Macs, a Windows setup program.

**Lesson.** The Claude Code format-on-edit hook ran `ruff --fix` between two edits and deleted an import that wasn't
used yet. It now only sorts imports and formats; unused imports are left to the stop gate and CI. Separately, the UI
tests had always crashed on exit about half the time (code 127) with every test passing: windows and their media
players were torn down after Qt. `tests/conftest.py` now deletes them at the end of the session.

## 2026-10-28: Open-source release, built for AI-assisted contributors, and a landing page

**Owner request.** Prepare the repo for open source with the usual practices (contributing, docs, tests), and make it
work well for vibe coding: guardrails, a harness, context, and *brief* developer docs ("attention spans are low"). The
main README stays simple and links out. Also: a landing page in this repo to promote the idea.

**Owner's choices.** MIT licence. Third-party skills **not** shipped (they stay on the owner's machine, listed in
`SKILLS.md` with pinned sources). The website in **Astro** (recommended plain HTML; the owner picked Astro).

**Done.**
- `AGENTS.md` is the single source of instructions for every agent; `CLAUDE.md` imports it and adds Claude-only notes.
  `website/AGENTS.md` covers the site.
- One check, `tools/check.py` (ruff lint, ruff format, all tests), run by CI on Windows, `check.bat` and the agents.
- `tests/test_guardrails.py` turns the written rules into checks: Qt stays out of the core, colours only from the
  theme, dialogs through the remembering helpers, the known Qt traps, the voice (banned words, `!`, emoji), no secrets,
  personal paths or big files, and doc links that resolve. Older off-voice messages are listed in `KNOWN_COPY_DEBT`,
  which may only shrink (listed as a good first issue in `docs/roadmap.md`).
- `tools/screenshots.py` renders the real window in Booth and Daylight with a generated demo vocal, without showing it
  and without the `offscreen` platform; `--site` refreshes the website's images, so the site shows the real app.
- Claude Code: shared settings ask before editing guardrails, CI or settings and before pushing, and never read `.env`
  or the saved Spotify login; hooks format edited Python and send Claude back once if lint or guardrails fail.
- The code was formatted with ruff once (layout only, tests unchanged and passing); the palette tables in `theme.py`
  are excluded so they stay one row per colour role. Dependencies pinned to the versions the tests pass with.
- The music folder placeholder no longer shows the owner's folder name; personal paths removed from this log.
- The old README's how-to moved to `docs/user-guide.md`.

**Why.** Rules in docs drift and agents skim them; rules in tests hold. Looking at real screenshots caught most visual
bugs in this project, so the harness makes looking one command.

**The website (`website/`).** The idea comes from the product: *the page counts you in.* Four bars light up at 124 BPM,
then the amber downbeat, and the app's screenshot lands on it. Its one interactive part is the app's own model: tap four
beats, a straight-line fit locks the grid (like `align.fit_grid`), and *Hear the count-in* plays four clicks and a note
on the one. Every picture is a real screenshot from `tools/screenshots.py --site`; tutorial text is read from
`assets/tutorials/tutorials.json`. The `design-taste-frontend` skill's written guidance was followed and its scripts
were not run (project rule). Where its house rules clash with the brand, the brand wins: soft shadows only on the app
screenshots (they are floating windows), a hairline edge on dark panels in Booth, rounded corners as in the app. No
trackers, no web fonts, no third-party requests; Astro's telemetry is switched off in CI. Checked in real Chrome at
1440, 768 and 390 px in both looks; two class-name collisions between page and component styles were found that way
and fixed (page classes now have page-only names).

**Published** the same day at [github.com/tomgreef/dj-toolkit](https://github.com/tomgreef/dj-toolkit), with
GitHub Pages (built by Actions) and private vulnerability reporting turned on. The site:
[tomgreef.github.io/dj-toolkit](https://tomgreef.github.io/dj-toolkit/).

**Open.** The owner has seen the website in the preview but hasn't given a verdict yet.

## 2026-10-27: Colours: "too clinical", wants shadcn/ui and award-winning websites

**Owner feedback.** Only the colours: the app feels **too clinical**. They are not a designer but prefer how *websites*
look, like **shadcn/ui components**: rounded corners, floating things, a clear CTA. Also: "think about which websites
were awarded for best UI/UX and use them as inspiration."

**Inspiration researched.** Awwwards Site of the Year 2025 ([Lando Norris](https://www.awwwards.com/websites/sites_of_the_year/),
Messenger), CSS Design Awards 2025 (Best UI: Exat Typeface; Best UX and overall: Dropbox Brand),
[Webby 2026 Best User Experience](https://winners.webbyawards.com/winners/websites-and-mobile-sites/features-design/best-user-experience)
honorees (Google Gemini, Air.inc, Nikon, The Wildlife Society), the Readymag "websites of 2025" write-up, and the 56
palettes distilled from award-style sites in the installed `design-taste-frontend` skill (`library/palettes.json`).
What they share, and what we took: **warm tactile neutrals** (bone, putty, stone, soft black) instead of cold greys;
**one accent spent on the single CTA and tiny markers**; **type-led hierarchy** (big confident headings); **one strong
inverted moment** on an otherwise quiet page; expressive-but-intentional personality.

**Done (colours and presentation only; no behaviour changed).**
- Warm neutrals: Daylight is bone paper with warm-white cards; Booth is soft warm black. (`ui/theme.py`)
- **Floating cards**: rounded (14), hairline border, a soft shadow painted by `widgets.Panel` itself (QSS can't do
  shadows; a `QGraphicsEffect` would re-render the waveform every playhead tick). The primary action sits on its own
  floating bar. Controls radius 8, pills fully round, CTA bigger and bolder.
- The waveform is a **dark "stage" in both modes** (a CDJ-display moment, the award sites' inverted band).
- Headings in Segoe UI Variable Display (friendlier); Bahnschrift (DIN, the clinical one) kept only for numbers.
- **Accent picker** (Mono grey is the default for new people, per the owner; Violet, Blue, Emerald, Rose are one click away) in the sidebar, like shadcn's theme colours, because
  colour had been uncertain for several rounds: let the owner choose by eye. Amber stays reserved for the downbeat
  marker so it never means anything else.
- `tests/test_theme.py` now checks every mode x accent combination (text 4.5:1, outlines and data marks 3:1, the stage).
  It caught two real misses (light-mode green and Emerald's link on the warm background) before the owner saw them.

**Open.** If it still isn't right, try (in order): another accent; more or less shadow (`_BASE[...]["shadow"]` alpha);
card radius (`R_PANEL`); a warmer or cooler neutral ladder; a brighter stage. Ask the owner what feels off in their own words.

## 2026-10-27: Alignment should work like Ableton (two steps, playhead, scratch)

**Owner feedback (paraphrased):** Acapella prep is difficult to align. They like how smooth Ableton is: you see the
track playing in the waveform and can *scratch it back* to set markers on the right beat. Idea: the user should focus on
setting **the four beats at the main chorus** first. Once that is right, set **the start of the track** ("4 beats and the
next one it drops in").

**Done.**
- Step 1, *Lock the grid*: four numbered beat markers at the loudest part of the track. The tempo and phase of the grid
  are a least-squares fit through them (`audio/align.py`), so four careful clicks beat any detector.
- Step 2, *Set the start*: click the beat where the vocal comes in; it snaps to the grid. The count-in is the beats before it.
- Playhead + clock, Space to play, a **loop** over the four beats, a **metronome click** on the grid beats (hear whether
  the grid is on the music), **B** taps beats while listening, and a **scrub strip** along the top: dragging it
  scratches (forward, backward, speed follows the hand, silent when you stop) via `audio/transport.py` and a Qt
  `QAudioSink` pull device (`ui/audio_output.py`). Dragging a marker also scrubs, so you hear it as you move it.
- The detector is now only a *suggestion*: it places the four beats at the loudest 8-bar stretch and snaps them to real
  onsets (`refine_to_onsets`), and puts the start on the grid. The owner is expected to check by ear and drag.
- The four beats and the start are remembered per file.

**Why.** Auto-detecting the downbeat of an a cappella is unreliable (no drums), and a single marker on a flat waveform
gives no way to *hear* alignment. Looping a chorus with a click is how DJs and producers verify a grid.

**Open / not verified.**
- Never tested with real acapellas, and not by ear (the build machine can't judge audio). The logic and the audio-device
  handshake are tested; tap-latency compensation uses a fixed 50 ms output buffer and may need calibration.
- Ideas not built: audible start-marker audition (click on a grid beat while scrubbing), snapping markers to onsets as you
  drag, a "phrase" (8/16-bar) view, time-stretching to a target BPM, batch mode.

## 2026-10-27: Persona-driven wording and remembered settings

**Owner request.** Colours are liked but "maybe it is the way it is presented". Focus on UX *wording* and presentation:
identify the crowd (what a DJ sees every day: lights, rekordbox, clubs, parties, day-beach parties), build a persona,
and base all wording on it. Also: **save last settings**, e.g. if I pick a sample from folder X, open there next time,
with a fallback if it's deleted. And **record these observations** so future Claude sessions (even in an open-sourced
repo) understand the concerns and approaches.

**Done.**
- `docs/ux/PERSONA.md` (Rio, a working DJ, *assumed not researched*) and `docs/ux/VOICE.md` (voice, tone by moment,
  glossary, checklist). All UI strings rewritten to match; a grep audit found no banned words or jargon left.
- Modes renamed **Booth** (dark) and **Daylight** (light) with tooltips, because a day-beach party in the sun is a
  *use case* for light mode, not a preference.
- Remembered (in `%APPDATA%\DJToolkit\settings.json`): the folder each dialog last used (acapella, sample, export,
  imports, music folder), the last acapella (offered as "Reopen …" while it exists), the four beats and start per file,
  count-in type/length/sample, export format/folder, window size and place, page, last tutorial, theme.
- **Fallbacks** (all tested): a deleted dialog folder → the nearest existing parent → Music → home; a deleted count-in
  sample → back to Audible click with a message; an export folder on a drive that isn't plugged in → saves next to
  the original and says so; a changed file ignores stale per-file memory.
- Sync: Spotify "Link Spotify" wording; "Sync playlists" button; confirmation names the consequence and the safe part.

**Open.** Validate the persona and words with real DJs (questions listed at the bottom of PERSONA.md). The owner has not
yet said whether the *colours* feel right after the wording work; see the entry below.

## 2026-10-27: Design skills, redesign and colours

**Owner feedback.** Didn't like the original mint/teal colours. After the redesign: "I'm liking the styling … not sure
I'm 100% on the colours yet, maybe it is the way it is presented."

**Done.** Installed four design skills (see `SKILLS.md`), redesigned around a blue-black "stage" ground, cobalt
(primary action + waveform) and amber (cue/downbeat marker). Left sidebar naming the product, flat panels, drawn icons,
Bahnschrift numerals, light/dark with WCAG-tested contrast (`tests/test_theme.py`).

**Interpretation to keep in mind.** The owner's hint is that the *presentation* (voice, framing, personality), not only
the hues, may be what feels off. The persona/wording work above is the first response. If colour is still wrong, try
changing the *feel* before the hue: warmer neutrals, a less corporate primary, amber/pink "club light" accents on data,
softer elevation. Palettes are one place (`ui/theme.py` `DARK`/`LIGHT`); run `pytest tests/test_theme.py` after editing.

## 2026-10-27: Tutorials and Spotify

- **Tutorials must be KISS** ("SUPER SIMPLE"): one recommendation sentence and 2 to 4 short steps. A test enforces it.
  A discussion box lets people question the recommendation, anonymously ("Anonymous DJ #xxxx"), stored locally behind a
  `Forum` interface so a shared online forum can replace it. Content is a **draft**; the rekordbox steps are unverified.
- **Spotify is "each folder becomes a playlist".** The tab was renamed from Genre Sync. The owner has **not yet tested
  with a real API key** and will. "Sync playlists" is gated behind a preview (added by us, not requested).
- A guided Spotify setup (six steps, annotated mock images; real screenshots in `assets/setup/real/` override them).

## 2026-10-27: Stack and first decisions

- Owner chose **Python + PySide** (over Electron/Tauri), count-in **"both, selectable"** (click / silence / own sample,
  default click), annotated **mock screenshots** for the Spotify guide, and asked us to install Python 3.12 via winget.
- The Python Spotify matcher was verified identical to the owner's TypeScript tool on 1000 real tracks (scores and URIs).
  The owner's old settings used `MATCH_THRESHOLD=0.7`.
- BPM detection is ±0.5 on real tracks and makes octave errors (Half / Double fix it). Beat 1 comes from the first sound,
  not the tracker (tracker times carry ~10 ms of latency).

## Process lessons (so we don't repeat them)

- Bugs were found by **running the real window** and tests that mimic the user, not by reading code: a spin box
  collapsing to 1 px, a `1 << 20 + x` precedence bug that overflowed the audio device, a renamed palette field that
  would have crashed on successful Spotify linking, a test whose "beats" were off the real hits.
- The sandbox **blocked running a downloaded skill's Python script** and a command containing `rm -rf "$VAR"`. Both
  refusals were right; we worked around neither (see `SKILLS.md`).

## Before open-sourcing (decisions for the owner)

Resolved on 2026-10-28 (see the entry at the top): the skills are not shipped, and personal paths are gone.
Still open:

- Ship real (not mock) Spotify setup screenshots, or keep the mocks labelled as illustrations.
- Packaging: done on 2026-10-28 (downloads for Windows and macOS, see that entry).
- Persona and tutorials: label clearly as hypotheses; invite DJs to challenge them (the forum is the intended place).
