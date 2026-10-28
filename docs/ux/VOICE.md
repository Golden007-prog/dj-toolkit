# Voice and tone

Voice is who we are (constant). Tone is how we adjust to what Rio is feeling right now. Read
`PERSONA.md` first. Built from the open-source `ux-copy`, `ux-writing` and `persona-*` skills in
`.claude/skills/`, adapted to this product.

## Voice: "the calm friend in the next booth"

| Trait | Means | Sounds like | Never sounds like |
|---|---|---|---|
| **Calm** | Unhurried, even when something broke | "That file didn't open. Try WAV, MP3 or FLAC." | "Oops! Something went wrong!!" |
| **Plain** | Short words, active verbs, one idea per sentence | "Mark the downbeat." | "Utilise the beat-anchoring functionality." |
| **Dry warmth** | A trace of personality, never a joke at Rio's expense | "Saved. Ready for the USB." | "Boom! You're a legend! 🎉" |
| **Honest** | Say what will happen, including the risky part | "Tracks no longer in a folder are removed from its playlist." | "Syncing your library…" |
| **Respectful of attention** | Front-load the action, cut the rest | "Preview first. Nothing changes on Spotify." | "Before you proceed, please note that…" |

The brand is *not* a hype-man, a robot, or a teacher. One small piece of club culture per screen at most,
and only where it also adds clarity.

## Tone by moment

| Rio is… | Moment | Tone | Example |
|---|---|---|---|
| **Focused** | Normal prep | Efficient, minimal | "Reads 128.00 BPM. Downbeat at 1.200 s." |
| **Unsure** | First run, Spotify setup | Patient, one step at a time, explain why | "Spotify wants an app registered. It's just a key for DJ Toolkit." |
| **Worried** | An error, a missing file | Steady, no blame, always a next step | "Couldn't reach that folder. Is the drive plugged in?" |
| **Cautious** | Anything that deletes or overwrites | Serious, specific, names the consequence | "Remove 12 tracks from 3 playlists? Your music files aren't touched." |
| **Done** | Success | Brief, specific, no fanfare | "Saved. Ready for the USB." |

## Copy patterns

- **Buttons:** verb + object, sentence case: *Open acapella, Preview, Export, Sync playlists.*
  Never "OK", "Submit", "Click here". Confirmation buttons name the action ("Sync playlists" / "Not yet").
- **Errors:** *What happened. Why (if we know). What to do.* One to three short sentences.
  No codes, no blame ("invalid"), no "An error occurred". Always a way forward.
- **Empty states:** *What this is. Why it's empty. How to start.*
- **Confirmations:** name the action and the consequence; buttons repeat the action.
- **Tooltips:** only what the label can't say. Include the keyboard shortcut.
- **Titles:** a noun, sentence case ("Acapella prep"). Subtitle: one plain sentence about the job, never about the interface.
- **Numbers:** always with units (128.00 BPM, 1.200 s). Counts say what they count ("12 tracks").
- **Tense:** present for state ("Reads 128 BPM"), past for done ("Saved"), imperative for actions ("Mark the downbeat").

## Glossary (one name per thing, everywhere)

| Say | Not | Why |
|---|---|---|
| **Downbeat** (help text: "the one") | beat 1, first beat | The word DJs use. |
| **Count-in** | lead-in, preroll | Short, musical, matches the feature. |
| **Folder** (on disk) / **playlist** (Spotify) | genre, crate, directory | Rio knows folders; "genre" is our internal field name. |
| **Booth** / **Daylight** (modes) | Dark / Light | Names the use case. Tooltip gives the plain words. |
| **Preview** | dry run | Plain. |
| **Match strictness** | confidence threshold | Plain. Helper: "Higher means fewer wrong matches." |
| **Spotify searches** | lookups, API calls | Plain. |
| **Link Spotify** / **linked** | authorize, connected via OAuth | Plain. |
| **Tempo** (BPM) | tempo detection algorithm | Rio says BPM. |
| **Sync playlists** | mirror, apply | Says the outcome. |
| **Lock the grid** (step 1) / **Set the start** (step 2) | align, warp, quantize | Names what Rio is doing, in order. |
| **Four beats** (marked at the chorus) | anchor points, warp markers | Says how many and where. |
| **Vocal starts at** / **Start** | downbeat position, cue offset | The thing Rio is placing. |
| **Remembered** (searches, alignment) | cached, persisted | Rio doesn't say "cache". |

## Words and habits to avoid

`Oops`, `Awesome!`, `Whoops`, `Unfortunately`, `invalid`, `illegal`, `Please` (as filler), `Click here`,
`Error`, `Success!`, emoji, exclamation marks, ALL CAPS labels, "we" (the tool is not a person),
puns on "drop"/"beat" in functional text, and any mention of PKCE, tokens, caches or thresholds.

## Checklist before shipping a string

1. Would Rio understand it in two seconds? (Read it aloud.)
2. Does it start with the action or the answer?
3. Is every word doing a job? Cut one.
4. Does it use the glossary term, exactly?
5. If it's an error: does it say what happened, why, and what to do?
6. If it's risky: does it name the consequence and the safe part?
7. Is it sentence case, no exclamation mark, no emoji?
8. Does the same thing have the same name on every screen?

## Reviewing copy

Use the installed skills as a second opinion, in this order: `ux-copy` (patterns), `ux-writing`
(accessibility and benchmarks), `ux-microcopy-audit` (scan the code for weak strings),
`persona-review` (judge it as Rio). See `SKILLS.md`.
