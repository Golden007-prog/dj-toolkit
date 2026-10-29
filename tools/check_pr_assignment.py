"""Say so, once, when a pull request fixes an issue that isn't assigned to its author, and once when it names no
issue at all unless it changes only docs (CONTRIBUTING.md, steps 1 and 3).

Run by .github/workflows/pr-assignment.yml with REPO ("owner/name") and PR (a number) in the environment. The workflow
runs on pull_request_target, so it holds a token that can write to pull requests from forks, and it always fetches
this file from main. This script reads the pull request through the GitHub CLI (its list of changed files too, never
the files) and never checks out, builds or runs anything the pull request holds. It posts at most one comment of each
kind and nothing else: it never closes, labels or blocks a pull request.

The decisions are `issues_to_flag` and `needs_an_issue`, pure functions; `run` only fetches the facts and posts.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence

MARKER = "<!-- pr-assignment -->"  # in the comment, so a pull request never gets it twice
NO_ISSUE_MARKER = "<!-- pr-no-issue -->"  # the same, for the comment that asks which issue it is for
MAINTAINERS = {"OWNER", "MEMBER", "COLLABORATOR"}  # GitHub's author_association for people who can assign the issue
BOTS = {"dependabot[bot]", "Copilot"}  # GitHub's logins for them; their pull requests are audited another way


def exempt(author: str, association: str) -> bool:
    return association in MAINTAINERS or author in BOTS


def issues_to_flag(
    author: str,
    association: str,
    assignees: Mapping[int, Sequence[str]],
    comments: Sequence[str],
) -> list[int]:
    """The issues the pull request says it fixes that aren't assigned to its author. Empty means say nothing.

    assignees maps each of those issues to the logins assigned to it; comments are the bodies of the comments
    already on the pull request."""
    if exempt(author, association) or any(MARKER in body for body in comments):
        return []
    return sorted(n for n, logins in assignees.items() if author.casefold() not in {x.casefold() for x in logins})


def docs_only(files: Sequence[str], total: int) -> bool:
    """Every file the pull request changes is a Markdown file or under docs/. total is how many files it changes in
    all: a shorter list hasn't shown them all, so it can't be called docs only."""
    return len(files) == total and all(f.endswith(".md") or f.startswith("docs/") for f in files)


def needs_an_issue(
    author: str,
    association: str,
    closing: Sequence[int],
    files: Sequence[str],
    total: int,
    comments: Sequence[str],
) -> bool:
    """True when the pull request names no issue and changes more than docs, and hasn't been asked yet.

    closing holds the issues it says it fixes, in any repository; files are the paths it changes and total is how many
    files it changes in all; comments are the bodies of the comments already on the pull request."""
    if exempt(author, association) or any(NO_ISSUE_MARKER in body for body in comments):
        return False
    return not closing and not docs_only(files, total)


def _refs(numbers: Sequence[int]) -> str:
    refs = [f"#{n}" for n in numbers]
    return refs[0] if len(refs) == 1 else ", ".join(refs[:-1]) + " and " + refs[-1]


def _rule_url(repo: str) -> str:
    return f"https://github.com/{repo}/blob/main/CONTRIBUTING.md#from-issue-to-merged-pull-request"


def comment_for(repo: str, numbers: Sequence[int]) -> str:
    """What it saw, why the rule exists, what to do (docs/ux/VOICE.md)."""
    one = len(numbers) == 1
    that = "that issue isn't" if one else "those issues aren't"
    return (
        f"{MARKER}\n"
        f"This pull request says it fixes {_refs(numbers)}, but {that} assigned to you.\n\n"
        "An issue is assigned before anyone builds it, so two people don't build the same thing "
        f"([step 3 in CONTRIBUTING.md]({_rule_url(repo)})).\n\n"
        f"What to do: comment on {'it' if one else 'each one'} that you'd like to take it, and wait for a maintainer "
        "to assign you. GitHub only lets a maintainer assign someone from outside once they have commented there.\n\n"
        "This note doesn't close or block your pull request."
    )


def comment_for_no_issue(repo: str) -> str:
    """What it saw, why the rule exists, what to do (docs/ux/VOICE.md)."""
    return (
        f"{NO_ISSUE_MARKER}\n"
        "This pull request doesn't say which issue it fixes.\n\n"
        "An issue is assigned before anyone builds it, so two people don't build the same thing "
        f"([steps 1 and 3 in CONTRIBUTING.md]({_rule_url(repo)})).\n\n"
        "What to do: open an issue for this change, or find the one it belongs to, and comment there that you'd like "
        "to take it. GitHub only lets a maintainer assign someone from outside once they have commented there. "
        "When you are assigned, add a line like `Fixes #123` to the description of this pull request, with that "
        "issue's number.\n\n"
        "This note doesn't close or block your pull request."
    )


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, stdout=subprocess.PIPE, text=True, timeout=60).stdout


def run(repo: str, pr: int, gh: Callable[..., str] = gh) -> str:
    """Look at one pull request, comment if the rule needs it, and return a line saying what happened."""
    who = json.loads(
        gh("api", f"repos/{repo}/pulls/{pr}", "--jq", "{author: .user.login, association: .author_association}")
    )
    if exempt(who["author"], who["association"]):
        return f"#{pr}: {who['author']} ({who['association']}) is not checked."
    view = json.loads(
        gh("pr", "view", str(pr), "--repo", repo, "--json", "closingIssuesReferences,comments,files,changedFiles")
    )
    comments = [c["body"] for c in view["comments"]]
    closing = [ref["number"] for ref in view["closingIssuesReferences"]]
    files = [f["path"] for f in view["files"]]
    if needs_an_issue(who["author"], who["association"], closing, files, view["changedFiles"], comments):
        gh("pr", "comment", str(pr), "--repo", repo, "--body", comment_for_no_issue(repo))
        return f"#{pr} by {who['author']} names no issue: asked which one it is for."
    assignees = {}
    for ref in view["closingIssuesReferences"]:
        if f"{ref['repository']['owner']['login']}/{ref['repository']['name']}".casefold() == repo.casefold():
            issue = json.loads(gh("issue", "view", str(ref["number"]), "--repo", repo, "--json", "assignees"))
            assignees[ref["number"]] = [a["login"] for a in issue["assignees"]]
    flagged = issues_to_flag(who["author"], who["association"], assignees, comments)
    seen = f"#{pr} by {who['author']} fixes {_refs(sorted(assignees)) if assignees else 'no issue here'}"
    if not flagged:
        return f"{seen}: nothing to say."
    gh("pr", "comment", str(pr), "--repo", repo, "--body", comment_for(repo, flagged))
    return f"{seen}: commented about {_refs(flagged)}."


def main() -> int:
    print(run(os.environ["REPO"], int(os.environ["PR"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
