// Where the code lives. On GitHub Actions this comes from the repository itself (owner/name);
// set REPO=owner/name to point the links at a fork.
const repo = process.env.REPO || process.env.GITHUB_REPOSITORY || "tomgreef/dj-toolkit";
const url = `https://github.com/${repo}`;

export const links = {
  repo: url,
  clone: `${url}.git`,
  source: `${url}/blob/main/docs/getting-started.md`,
  contributing: `${url}/blob/main/CONTRIBUTING.md`,
  vibe: `${url}/blob/main/docs/vibe-coding.md`,
  roadmap: `${url}/blob/main/docs/roadmap.md`,
  guide: `${url}/blob/main/docs/user-guide.md`,
  feedback: `${url}/issues/new?template=dj_feedback.yml`,
  suggest: `${url}/issues/new?template=idea.yml`,
  bug: `${url}/issues/new?template=bug_report.yml`,
  ideas: `${url}/issues?q=is%3Aissue+is%3Aopen+label%3Aidea+sort%3Areactions-%2B1-desc`,
  discussions: `${url}/discussions`,
  licence: `${url}/blob/main/LICENSE`,
};

/** A path inside the site, correct whether it's served at / or at /dj-toolkit/ on GitHub Pages. */
export function asset(path: string): string {
  const base = import.meta.env.BASE_URL.endsWith("/") ? import.meta.env.BASE_URL : `${import.meta.env.BASE_URL}/`;
  return `${base}${path.replace(/^\//, "")}`;
}

// ---- Read from GitHub when the site is built (the Pages workflow rebuilds it every day). Never fails the build.

async function github(path: string): Promise<any | null> {
  const headers: Record<string, string> = { Accept: "application/vnd.github+json", "User-Agent": "dj-toolkit-website" };
  if (process.env.GITHUB_TOKEN) headers.Authorization = `Bearer ${process.env.GITHUB_TOKEN}`;
  try {
    const r = await fetch(`https://api.github.com/${path}`, { headers, signal: AbortSignal.timeout(8000) });
    return r.ok ? await r.json() : null;
  } catch {
    return null; // offline, or GitHub is busy: the page says where the list lives instead
  }
}

export type Idea = { number: number; title: string; votes: number; url: string };

/** The most-voted open ideas: each is an issue labelled "idea", and a thumbs-up reaction is a vote. */
export async function topIdeas(limit = 6): Promise<Idea[] | null> {
  const q = encodeURIComponent(`repo:${repo} is:issue is:open label:idea`);
  const data = await github(`search/issues?q=${q}&sort=reactions-%2B1&order=desc&per_page=30`);
  if (!data?.items) return null;
  return data.items
    .map((i: any) => ({ number: i.number, title: i.title, votes: i.reactions?.["+1"] ?? 0, url: i.html_url }))
    .sort((a: Idea, b: Idea) => b.votes - a.votes || a.number - b.number)
    .slice(0, limit);
}

export type Downloads = { version: string; windows: string; mac: string };

/** The latest release's downloads, only when both builds are there (so the page never links to nothing). */
export async function downloads(): Promise<Downloads | null> {
  const rel = await github(`repos/${repo}/releases/latest`);
  const find = (name: string) => rel?.assets?.find((a: any) => a.name === name)?.browser_download_url as string;
  const windows = find("DJ-Toolkit-Windows.zip");
  const mac = find("DJ-Toolkit-macOS.dmg");
  return windows && mac ? { version: rel.tag_name, windows, mac } : null;
}
