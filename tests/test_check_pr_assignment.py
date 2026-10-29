"""The check that a pull request's issue is assigned to its author (tools/check_pr_assignment.py, run by
.github/workflows/pr-assignment.yml). The decision is a pure function, so these need no GitHub: `FakeGitHub` stands in
for the `gh` command."""

import json
import re

import pytest

from tools import check_pr_assignment as rule

OUTSIDER = "FIRST_TIME_CONTRIBUTOR"


def flagged(author="newcomer", association=OUTSIDER, assignees=None, comments=()):
    return rule.issues_to_flag(author, association, {57: []} if assignees is None else assignees, comments)


# ------------------------------------------------------------- the decision
def test_an_unassigned_issue_gets_a_comment():
    assert flagged() == [57]


def test_an_issue_assigned_to_someone_else_gets_a_comment():
    assert flagged(assignees={57: ["somebody-else"]}) == [57]


def test_an_issue_assigned_to_its_author_gets_none():
    assert flagged(assignees={57: ["newcomer"]}) == []
    assert flagged(assignees={57: ["somebody-else", "newcomer"]}) == []


def test_logins_match_whatever_their_case():
    assert flagged(author="NewComer", assignees={57: ["newcomer"]}) == []


def test_only_the_issues_that_are_not_assigned_are_named():
    assert flagged(assignees={58: [], 57: ["newcomer"], 12: ["somebody-else"]}) == [12, 58]


def test_a_pull_request_with_no_issue_gets_none():
    assert flagged(assignees={}) == []


@pytest.mark.parametrize("association", ["OWNER", "MEMBER", "COLLABORATOR"])
def test_maintainers_are_skipped(association):
    assert flagged(association=association) == []


@pytest.mark.parametrize("association", ["CONTRIBUTOR", "FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER", "NONE", ""])
def test_everyone_else_is_checked(association):
    assert flagged(association=association) == [57]


@pytest.mark.parametrize("author", ["dependabot[bot]", "Copilot"])
def test_dependabot_and_copilot_are_skipped(author):
    assert flagged(author=author, association="CONTRIBUTOR") == []


def test_it_never_says_the_same_thing_twice():
    already = [rule.comment_for("tomgreef/dj-toolkit", [57])]
    assert flagged(comments=["Thanks for the pull request", *already]) == []


def test_other_comments_do_not_stop_it():
    assert flagged(comments=["Is this ready for review?"]) == [57]


# ------------------------------------------------------------- the comment
def test_the_comment_says_what_it_saw_why_and_what_to_do():
    text = rule.comment_for("tomgreef/dj-toolkit", [57])
    assert text.startswith(rule.MARKER)
    assert "says it fixes #57, but that issue isn't assigned to you" in text
    assert "two people don't build the same thing" in text
    assert "blob/main/CONTRIBUTING.md#from-issue-to-merged-pull-request" in text
    assert "comment on it" in text and "wait for a maintainer to assign you" in text
    assert "doesn't close or block" in text


def test_the_comment_names_every_issue():
    text = rule.comment_for("tomgreef/dj-toolkit", [12, 57, 58])
    assert "fixes #12, #57 and #58, but those issues aren't assigned to you" in text
    assert "comment on each one" in text


def test_the_comment_follows_the_voice_guide():
    """docs/ux/VOICE.md: no exclamation marks, no emoji, no filler, no 'we'; and no em dashes in anything public."""
    text = rule.comment_for("tomgreef/dj-toolkit", [57]).removeprefix(rule.MARKER)  # the hidden marker has a "!"
    assert text.isascii() and "!" not in text
    assert not re.search(r"\b(please|oops|whoops|unfortunately|invalid|we)\b", text, re.I)


# ------------------------------------------------------------- the glue
class FakeGitHub:
    """The `gh` command, for one pull request. Comments it is asked to post show up on the pull request."""

    def __init__(self, author="newcomer", association=OUTSIDER, closing=(57,), assignees=None, foreign=()):
        self.who = {"author": author, "association": association}
        self.closing = [("tomgreef", "dj-toolkit", n) for n in closing] + list(foreign)
        self.assignees = assignees or {}
        self.comments: list[str] = []
        self.calls: list[tuple] = []

    def __call__(self, *args):
        self.calls.append(args)
        if args[0] == "api":
            return json.dumps(self.who)
        if args[:2] == ("pr", "view"):
            refs = [{"number": n, "repository": {"name": r, "owner": {"login": o}}} for o, r, n in self.closing]
            return json.dumps({"closingIssuesReferences": refs, "comments": [{"body": b} for b in self.comments]})
        if args[:2] == ("issue", "view"):
            return json.dumps({"assignees": [{"login": x} for x in self.assignees.get(int(args[2]), [])]})
        if args[:2] == ("pr", "comment"):
            self.comments.append(args[args.index("--body") + 1])
            return ""
        raise AssertionError(f"unexpected gh call: {args}")

    @property
    def posted(self):
        return [c for c in self.calls if c[:2] == ("pr", "comment")]


def test_it_comments_once_however_often_it_runs():
    github = FakeGitHub()
    assert "commented about #57" in rule.run("tomgreef/dj-toolkit", 9, github)
    assert "nothing to say" in rule.run("tomgreef/dj-toolkit", 9, github)  # a reopened pull request
    assert len(github.posted) == 1
    assert github.posted[0][2] == "9" and github.posted[0][3:5] == ("--repo", "tomgreef/dj-toolkit")


def test_it_says_nothing_when_the_issue_is_assigned_to_the_author():
    github = FakeGitHub(assignees={57: ["newcomer"]})
    assert "nothing to say" in rule.run("tomgreef/dj-toolkit", 9, github)
    assert not github.posted


def test_it_does_not_even_look_at_a_maintainers_pull_request():
    github = FakeGitHub(author="tomgreef", association="OWNER")
    assert "is not checked" in rule.run("tomgreef/dj-toolkit", 9, github)
    assert [c[0] for c in github.calls] == ["api"]


def test_an_issue_in_another_repository_is_not_ours_to_check():
    github = FakeGitHub(closing=(), foreign=[("someone", "else", 5)])
    assert "nothing to say" in rule.run("tomgreef/dj-toolkit", 9, github)
    assert not any(c[:2] == ("issue", "view") for c in github.calls)


def test_it_only_ever_reads_and_comments():
    """It must not close, label or block a pull request: every gh call is a read, or the one comment."""
    github = FakeGitHub()
    rule.run("tomgreef/dj-toolkit", 9, github)
    for call in github.calls:
        assert call[:2] in {("pr", "view"), ("issue", "view"), ("pr", "comment")} or (
            call[0] == "api" and "--method" not in call
        ), call
