# AGENTS.md (website)

The landing page for DJ Toolkit: one static page built with Astro, published to GitHub Pages. The repo-wide rules in
[../AGENTS.md](../AGENTS.md) still apply; these are the extra ones for the site.

## Commands (from `website/`)

| To | Run |
|---|---|
| Install once | `npm ci --ignore-scripts` (a package can hide code in an install script, and the build needs none) |
| Work on it | `npm run dev`, then open http://localhost:4321 |
| Check it builds | `npm run build` (CI runs this on every pull request) |
| See the production build | `npm run build` then `npm run preview` |
| Refresh the app screenshots | from the repo root: `.venv\Scripts\python tools\screenshots.py --site` |

## How it's put together

- `src/pages/index.astro` is the page, section by section. `src/components/` holds the parts: `TapTempo` (the
  four-beat demo), `Shot` (a screenshot in the current look), `LookSwitch` (Booth / Daylight), `BrandMark`, `Arrow`.
- `src/styles/global.css` holds the tokens and shared pieces; `page.css` the page layout, phone first.
- Tutorial titles and recommendations come from `../assets/tutorials/tutorials.json`, the file the app uses. Edit
  them there, never on the page.
- Screenshots in `public/screens/` and `public/og.jpg` are made by `tools/screenshots.py --site` from the real app.
  Don't edit or replace them by hand, and never show a mock-up as if it were the app.
- `src/site.ts` also reads two things from GitHub when the site is built: the most-voted ideas (issues labelled
  `idea`) and the latest release's downloads. Both fall back quietly when GitHub can't be reached, and the download
  buttons only appear once a release has both files. The Pages workflow rebuilds the site daily to refresh votes.
- Links to GitHub come from `src/site.ts`. On GitHub Actions they use the repository the site is built from; elsewhere `tomgreef/dj-toolkit`.

## Rules

- **Colours are tokens.** Every colour is a custom property in `global.css`, copied from the app's
  `djtoolkit/ui/theme.py`, so the app's contrast tests cover them. Booth and Daylight both work; check both.
- **Amber means the downbeat** (and the count-in), and nothing else, as in the app.
- **Words follow [VOICE.md](../docs/ux/VOICE.md):** calm, plain, sentence case, no exclamation marks, no emoji, no hype.
  Say what is true today, including what isn't tested yet.
- **Headlines stay at two lines or fewer at every width**, down to a 390 px phone.
- **No trackers, analytics, cookies or third-party requests.** No web fonts: Segoe UI and Bahnschrift on Windows,
  system fonts elsewhere.
- **Motion is optional.** Use transform and opacity only, keep everything visible without JavaScript, and honour
  `prefers-reduced-motion`.
- **Accessible:** real headings, alt text on every screenshot, visible focus, every control usable by keyboard.
- **Page classes get page-only names** (`hero-…`, `…-section`). Two collisions with component classes broke the
  layout once (`.countin`, `.status`).
- **Keep dependencies to Astro.** Ask before adding any package.

## Before you say it's done

1. `npm run build` passes.
2. Look at the page at 1440, 768 and 390 px wide, in Booth and in Daylight: no overflow, nothing clipped, headlines
   at two lines or fewer.
3. Try the four-beat demo with the mouse and with the keyboard (Tab to *Tap*, then Space).
