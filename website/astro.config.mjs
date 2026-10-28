// @ts-check
import { defineConfig } from "astro/config";

// GitHub Pages passes its address in (.github/workflows/pages.yml). Locally the site lives at the root.
export default defineConfig({
  site: process.env.SITE || "http://localhost:4321",
  base: process.env.BASE_PATH || "/",
  devToolbar: { enabled: false },
  vite: {
    // The tutorials are read from ../assets/tutorials/tutorials.json, the same file the app uses.
    server: { fs: { allow: [".."] } },
  },
});
