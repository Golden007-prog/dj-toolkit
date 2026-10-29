"""Say so, once, when a pull request fixes an issue that isn't assigned to its author (CONTRIBUTING.md, step 3).

Run by .github/workflows/pr-assignment.yml with REPO ("owner/name") and PR (a number) in the environment. The workflow
runs on pull_request_target, so it holds a token that can write to pull requests from forks, and it always fetches
this file from main. This script reads the pull request through the GitHub CLI and never checks out, builds or runs
anything the pull request holds. It posts one comment and nothing else: it never closes, labels or blocks a pull request.

The decision is `issues_to_flag`, a pure function; `run` only fetches the facts and posts.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence

MARKER = "<!-- pr-assignment -->"  # in the comment, so a pull request never gets it twice
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


def _refs(numbers: Sequence[int]) -> str:
    refs = [f"#{n}" for n in numbers]
    return refs[0] if len(refs) == 1 else ", ".join(refs[:-1]) + " and " + refs[-1]


def comment_for(repo: str, numbers: Sequence[int]) -> str:
    """What it saw, why the rule exists, what to do (docs/ux/VOICE.md)."""
    one = len(numbers) == 1
    that = "that issue isn't" if one else "those issues aren't"
    rule = f"https://github.com/{repo}/blob/main/CONTRIBUTING.md#from-issue-to-merged-pull-request"
    return (
        f"{MARKER}\n"
        f"This pull request says it fixes {_refs(numbers)}, but {that} assigned to you.\n\n"
        "An issue is assigned before anyone builds it, so two people don't build the same thing "
        f"([step 3 in CONTRIBUTING.md]({rule})).\n\n"
        f"What to do: comment on {'it' if one else 'each one'} that you'd like to take it, and wait for a maintainer "
        "to assign you. GitHub only lets a maintainer assign someone from outside once they have commented there.\n\n"
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
    view = json.loads(gh("pr", "view", str(pr), "--repo", repo, "--json", "closingIssuesReferences,comments"))
    assignees = {}
    for ref in view["closingIssuesReferences"]:
        if f"{ref['repository']['owner']['login']}/{ref['repository']['name']}".casefold() == repo.casefold():
            issue = json.loads(gh("issue", "view", str(ref["number"]), "--repo", repo, "--json", "assignees"))
            assignees[ref["number"]] = [a["login"] for a in issue["assignees"]]
    flagged = issues_to_flag(who["author"], who["association"], assignees, [c["body"] for c in view["comments"]])
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
