# Persona: Rio, the working DJ

> **Status: assumed, not researched.** This persona is a synthesis of public DJ-community sources
> (linked at the bottom) and the product owner's own experience as a DJ. It has **not** been validated
> with interviews. Treat it as a strong hypothesis and update it when real DJs tell you otherwise.
> If you change it, also review `VOICE.md`, then re-read every user-facing string (see the checklist there).

Every word in DJ Toolkit is written for **Rio**. When you are unsure how to phrase something, ask:
*would Rio understand it in two seconds, with one hand on a laptop and the other holding a drink?*

## Who Rio is

- **Rio (they/them), 29.** A working DJ with roughly 2 to 8 gigs a month: club nights, rooftop sessions,
  day-beach parties, the odd private party or wedding that pays the rent. Self-taught (YouTube, a DJ
  course, years of practice). Has a day job or is going full-time.
- **Plays house, disco, techno or similar, and brings acapellas** to bring a vocal in over a mix.
- **Gear:** a laptop with **rekordbox**, a USB stick, and **CDJs / XDJs** in the booth. Spotify is for
  digging and for listening on the way to a gig, never for playing out.
- **Library:** about a thousand tracks in folders by genre or vibe, kept on a drive. Prep happens on the
  laptop at home, late in the evening, tired after the day job.
- **Tech comfort:** fluent in audio language (BPM, bars, phrases, cues, key, EQ), allergic to software
  language (API, token, OAuth, cache, "mirror mode"). Will happily learn a tool, will not read a manual.

## What Rio sees every day

This is the visual and emotional world the interface lives next to. Borrow its *clarity*, not its
costume.

| Where | What Rio sees | What it means for the UI |
|---|---|---|
| **rekordbox** | The Collection tree, playlists, a coloured waveform with a beat grid, hot-cue and memory-cue markers, "analysing" progress bars, **Export mode** to a USB | Waveform + grid is home turf: make ours legible and familiar. Cue colours mean something, so amber is *only* for the downbeat marker. |
| **The booth (club)** | Near-dark room, jog-wheel displays showing BPM and time remaining, LED walls, strobes, haze, loud monitors | Dark mode must be calm and high-contrast. Never a bright flash. Big, glanceable numbers (our BPM readout). |
| **Day-beach party** | Direct sun on the laptop, sunglasses, heat, sand in the gear, glare that washes out dark screens | A real **light mode** is a *use case*, not a preference. We call the modes **Booth** and **Daylight**. |
| **Before the gig** | A packed bag, a USB that must work, a phone torch to find it, a group chat with the promoter | Prep tools must be fast and reassuring. Show exactly what will happen before it does. |
| **The scary moments** | "Media is missing" in rekordbox, hot cues lost between laptop and USB, a USB the CDJ won't read | Never surprise Rio. Never delete silently. Say what is safe ("Your music files aren't touched"). |
| **Off the clock** | Spotify crates, Beatport/Bandcamp digging, Instagram stories of sets, practice mixes | Spotify sync exists so Rio can listen to their own crates on the move. |

## What Rio is trying to do (jobs)

1. **Get gig-ready without a fuss.** Library in order, USB exported, nothing missing.
2. **Mix a vocal in on the one.** An acapella with a clean count-in so it lands on the downbeat first time.
3. **Keep crates and Spotify in step** so what Rio digs on the phone matches what is on the drive.
4. **Look like they know what they're doing**, with a tidy library and no fumbling.

## What Rio fears

- Being caught out mid-set: a track missing, the wrong BPM, a vocal landing off the beat.
- Losing work: cues, edits, playlists.
- Tools that feel like homework, or that talk down to them.
- Hype. Rio has seen a thousand "game-changing" apps.

## How Rio talks (use these words)

BPM, bars, phrase, the one (the downbeat), cue, drop, break, intro, outro, loop, key, set, gig, booth,
warm-up, closing, crate (a folder of tracks), digging, USB, prep, blend, acapella.

## What Rio does not say (avoid in the UI)

API, token, OAuth, PKCE, redirect URI (only where Spotify forces it, and then explain it),
cache, threshold, dry run, mirror mode, sync semantics, "genre" as a technical field name, "invalid",
"error occurred".

## The one-line brief for any copy

> Talk like the calm friend in the next booth who knows the gear, says it once, and has your back.

## Sources

- [rekordbox: "media is missing" (DJ TechTools forum)](https://forum.djtechtools.com/t/rekordbox-media-is-missing/66428)
- [rekordbox export mode (We Are Crossfader)](https://wearecrossfader.co.uk/blog/rekordbox-export-mode/)
- [rekordbox tips: export mode (We Are Crossfader)](https://wearecrossfader.co.uk/blog/rekordbox-tips-tricks-export-mode/)
- [USB export workflow best practices (DJ TechTools forum)](https://forum.djtechtools.com/showthread.php?p=765204)
- Product owner's lived experience as a working DJ (not independently verifiable).

## Open questions to validate with real DJs

- Is "downbeat" or "the one" the word Rio reaches for first? (We use *downbeat*, with *the one* in help text.)
- Do Rio and friends say "crate" or "folder" or "playlist"? (We say *folder* for the thing on disk, *playlist* for Spotify.)
- Is Booth / Daylight clearer than Dark / Light? (We show both: the name and the plain word in the tooltip.)
