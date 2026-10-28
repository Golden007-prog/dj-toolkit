---
name: screenshots
description: Render DJ Toolkit's real window in Booth (dark) and Daylight (light) and review the images. Use after any change to the UI, the theme, icons or user-facing text, or when the user asks how something looks.
---

# Screenshots

1. Run `.venv\Scripts\python tools\screenshots.py` (add `--accent violet` or another accent if the change involves
   colour). It writes `screenshots/<page>-booth.png` and `<page>-daylight.png` for every page, using a demo vocal
   and a throwaway settings folder.
2. Open **every** image you produced, in both themes, and look for:
   - text that is clipped, overlapping or wrapping badly; controls that collapsed or grew;
   - colours that are hard to read, or that changed in one theme only;
   - amber used for anything but the downbeat marker; a missing focus ring or tooltip on an icon-only button;
   - copy that breaks `docs/ux/VOICE.md` (glossary terms, sentence case, no exclamation marks, no emoji).
3. Fix what you find, run the check (`/check`), and render again.
4. Tell the user what you looked at and what changed. Attach or name the images that show it.
5. If the website's images should change too, run it with `--site`; that refreshes `website/public/screens/`.
