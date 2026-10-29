# DJ Toolkit website

The landing page, built with [Astro](https://astro.build/) and published to GitHub Pages.

```bat
cd website
npm ci --ignore-scripts
npm run dev
```

Then open http://localhost:4321. `npm run build` writes the site to `dist/`.

- **Publishing:** every push to `main` that changes `website/` (or the tutorials) runs `.github/workflows/pages.yml`.
  One-time setup in the repository: *Settings > Pages > Source: GitHub Actions*.
- **Screenshots** come from the real app: `.venv\Scripts\python tools\screenshots.py --site` from the repo root.
- **Telemetry:** Astro collects anonymous usage data unless you opt out. CI opts out; locally, run
  `npx astro telemetry disable` once.
- **Rules** for changing the site, for people and AI agents: [AGENTS.md](AGENTS.md).
