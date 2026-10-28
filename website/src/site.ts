// Where the code lives. On GitHub Actions this comes from the repository itself (owner/name);
// set REPO=owner/name to point the links at a fork.
const repo = process.env.REPO || process.env.GITHUB_REPOSITORY || "tomgreef/on-the-one";
const url = `https://github.com/${repo}`;

export const links = {
  repo: url,
  clone: `${url}.git`,
  run: `${url}#run-it`,
  contributing: `${url}/blob/main/CONTRIBUTING.md`,
  vibe: `${url}/blob/main/docs/vibe-coding.md`,
  roadmap: `${url}/blob/main/docs/roadmap.md`,
  guide: `${url}/blob/main/docs/user-guide.md`,
  feedback: `${url}/issues/new?template=dj_feedback.yml`,
  licence: `${url}/blob/main/LICENSE`,
};

/** A path inside the site, correct whether it's served at / or at /on-the-one/ on GitHub Pages. */
export function asset(path: string): string {
  const base = import.meta.env.BASE_URL.endsWith("/") ? import.meta.env.BASE_URL : `${import.meta.env.BASE_URL}/`;
  return `${base}${path.replace(/^\//, "")}`;
}
