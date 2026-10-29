"""Feature requests, bug reports and votes, through the project's GitHub issues.

One list for everyone: each open issue labelled "idea" is an idea, and a thumbs-up reaction on it is a vote. The app,
the website and GitHub all show the same list. This module reads it (no sign-in needed) and builds the links that open
GitHub's forms, pre-filled, in the browser. Voting itself happens on GitHub and needs a free account; the app never
asks for a login and stores no keys. Plain Python, no Qt (a guardrail test checks), so it is easy to test.
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from urllib.parse import urlencode

import requests

from . import __version__

REPO = "tomgreef/on-the-one"
REPO_URL = f"https://github.com/{REPO}"
SEARCH_URL = "https://api.github.com/search/issues"
ALL_IDEAS_URL = f"{REPO_URL}/issues?q=is%3Aissue+is%3Aopen+label%3Aidea+sort%3Areactions-%2B1-desc"
TIMEOUT_S = 10


@dataclass(frozen=True)
class Idea:
    number: int
    title: str
    votes: int
    url: str


class FeedbackUnavailable(Exception):
    """GitHub couldn't be reached or said no. The message is written to be shown as it is."""


def top_ideas(limit: int = 8, session=None) -> list[Idea]:
    """The most-voted open ideas, most votes first (ties: oldest first)."""
    http = session or requests
    params = {"q": f"repo:{REPO} is:issue is:open label:idea", "sort": "reactions-+1", "order": "desc", "per_page": 30}
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"DJ-Toolkit/{__version__}"}
    try:
        r = http.get(SEARCH_URL, params=params, headers=headers, timeout=TIMEOUT_S)
    except requests.RequestException as e:
        raise FeedbackUnavailable("Couldn't reach GitHub. Check your connection, then try again.") from e
    if r.status_code in (403, 429):
        raise FeedbackUnavailable("GitHub is busy right now. Try again in a minute.")
    if not r.ok:
        raise FeedbackUnavailable("GitHub didn't answer. Try again later.")
    ideas = [
        Idea(int(i["number"]), str(i["title"]), int((i.get("reactions") or {}).get("+1", 0)), str(i["html_url"]))
        for i in r.json().get("items", [])
    ]
    return sorted(ideas, key=lambda i: (-i.votes, i.number))[:limit]


def system_name() -> str:
    """The operating system, as a person would write it in a bug report."""
    if sys.platform == "darwin":
        return f"macOS {platform.mac_ver()[0]}".strip()
    if sys.platform == "win32":
        return f"Windows {platform.release()} ({platform.version()})"
    return platform.platform()


def suggest_url() -> str:
    """GitHub's form for a new idea."""
    return f"{REPO_URL}/issues/new?" + urlencode({"template": "idea.yml"})


def bug_url() -> str:
    """GitHub's bug form, with the app version and the system already filled in."""
    fields = {"template": "bug_report.yml", "version": __version__, "system": system_name()}
    return f"{REPO_URL}/issues/new?" + urlencode(fields)
