# User guide

[Read this guide in Chinese (中文)](zh/user-guide.md)

Everything the app does, on one page. On macOS, read Cmd wherever it says Ctrl.

## Acapella prep: two steps

Aligning is easiest where the beat is clearest, so you do it at the chorus, listening.

**1. Lock the grid.** The app suggests four beats in the loudest part of the track. Press **Space** to play: the four
beats loop and a **click** plays on the grid, so you hear whether it sits on the music. Fix a marker by dragging it
(you hear it as you drag), or clear them and click four beats in a row, or tap **B** along with the music.
Four careful beats set the tempo *and* the phase of the grid for the whole track.

**2. Set the start.** Click the beat where the vocal comes in; it snaps to the grid. The count-in is the beats before
it: a click, silence or your own sample. **Preview** plays the count-in, then the vocal. **Export** writes WAV, FLAC or
MP3 named `Name - 128bpm.ext`, with the BPM tagged.

| Do | How |
|---|---|
| Scratch back and forth | Drag the strip along the top of the waveform |
| Zoom / pan | Mouse wheel / Shift+wheel or right-drag |
| Nudge a marker | Click it, then `←` `→` (Shift: 1 ms, Ctrl: 100 ms) |
| Fix a double-time or half-time read | **Half** / **Double** |
| Switch pages | `Ctrl+1` `Ctrl+2` `Ctrl+3` |
| Open, preview, export | `Ctrl+O`, `Ctrl+P`, `Ctrl+E` |

## Spotify sync: each folder becomes a playlist

1. **Link Spotify.** The six-step guide walks you through creating a Spotify app, setting its Redirect URI to
   `http://127.0.0.1:8888/callback`, pasting the Client ID and approving access. If you changed the Callback port
   via More, update this URI to match.
2. **Choose your music folder.** Every folder inside it becomes a playlist.
3. **Preview changes** first. **Sync playlists** unlocks after a preview, because syncing removes tracks that are no
   longer in a folder. Changing any setting asks for a fresh preview. Your music files are never touched.
4. Spotify limits how many searches a new app can make in a day. Keep *Spotify searches per run* around 150 until your
   library is matched. Matches are remembered, and nothing is removed until matching is complete.

Coming from the old command-line tool? **More** has *Import the old tool's .env* and *Import the old tool's
searches*, so tracks you matched before aren't searched again.

## Tutorials

Short guides with one recommendation each: folder structure, folders to rekordbox, rekordbox to USB, acapellas, and
Spotify playlists. Disagree with one? Post a question or a challenge below it. You appear as *Anonymous DJ #xxxx*,
and for now posts stay on your computer.

## Requests

Vote on what gets built next. The page lists the most-wanted ideas, which are GitHub issues; **Vote** opens one on
GitHub, where a thumbs-up counts as a vote (you need a free GitHub account). **Suggest a feature** and **Report a bug**
open short forms on GitHub, with your app version already filled in. The app never asks for a login, and fetches the
list only when you open the page.

## What it remembers

The four beats and the start for each file you've worked on, the folder each dialog last used (with a fallback if
it's gone), your count-in and export choices, the window, the page, the last tutorial, and the look.
All of it lives in `%APPDATA%\DJToolkit` on Windows and `~/Library/Application Support/DJToolkit` on macOS.
Delete that folder to start fresh.

## Looks

The **Appearance** switch in the sidebar picks **Booth** (dark, for clubs and late-night prep) or **Daylight** (light
and high-contrast, for sunny day parties). The dots below it pick an accent colour.
