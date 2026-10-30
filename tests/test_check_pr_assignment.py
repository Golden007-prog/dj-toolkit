"""The check that a pull request's issue is assigned to its author, and that it names an issue at all
(tools/check_pr_assignment.py, run by .github/workflows/pr-assignment.yml). The decisions are pure functions, so these
need no GitHub: `FakeGitHub` stands in for the `gh` command."""

import json
import re

import pytest

from tools import check_pr_assignment as rule

OUTSIDER = "FIRST_TIME_CONTRIBUTOR"


def flagged(author="newcomer", association=OUTSIDER, assignees=None, comments=()):
    return rule.issues_to_flag(author, association, {57: []} if assignees is None else assignees, comments)


def asks(
    author="newcomer", association=OUTSIDER, closing=(), files=("djtoolkit/settings.py",), total=None, comments=()
):
    """Does `needs_an_issue` say to ask? By default: a pull request that names no issue and changes one code file."""
    total = len(files) if total is None else total
    return rule.needs_an_issue(author, association, closing, files, total, comments)


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


def test_a_pull_request_with_no_issue_has_none_to_flag():
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


# ------------------------------------------------------------- no issue at all
def test_a_pull_request_that_names_no_issue_gets_a_comment():
    assert asks()


def test_a_pull_request_that_names_an_issue_is_left_to_the_assignment_check():
    assert not asks(closing=[57])
    assert not asks(closing=[57, 58])


@pytest.mark.parametrize(
    "files",
    [
        ["README.md"],
        ["docs/maintaining.md"],
        ["docs/ux/screenshots/booth.png"],
        ["CONTRIBUTING.md", "docs/getting-started.md", "docs/ux/VOICE.md"],
    ],
)
def test_a_pull_request_that_changes_only_docs_gets_none(files):
    assert not asks(files=files)


@pytest.mark.parametrize(
    "files",
    [
        ["djtoolkit/settings.py"],
        ["README.md", "djtoolkit/settings.py"],  # one file that is not docs is enough
        ["docs.py"],  # "docs/" is a folder, not a prefix
        ["website/docs/page.astro"],  # only the top-level docs folder
        [".github/workflows/pr-assignment.yml"],
        ["tests/test_docs.md.py"],  # it ends in .py, whatever the middle says
    ],
)
def test_one_file_that_is_not_docs_is_enough(files):
    assert asks(files=files)


def test_a_list_of_files_that_is_cut_short_is_not_called_docs_only():
    assert asks(files=["README.md"], total=150)


@pytest.mark.parametrize("association", ["OWNER", "MEMBER", "COLLABORATOR"])
def test_maintainers_are_not_asked_for_an_issue(association):
    assert not asks(association=association)


@pytest.mark.parametrize("author", ["dependabot[bot]", "Copilot"])
def test_dependabot_and_copilot_are_not_asked_for_an_issue(author):
    assert not asks(author=author, association="CONTRIBUTOR")


def test_it_never_asks_for_an_issue_twice():
    already = [rule.comment_for_no_issue("tomgreef/dj-toolkit")]
    assert not asks(comments=["Thanks for the pull request", *already])


def test_the_two_comments_do_not_stop_each_other():
    """Each has its own marker: a pull request told about an unassigned issue can still be asked for one, and back."""
    assert asks(comments=[rule.comment_for("tomgreef/dj-toolkit", [57])])
    assert flagged(comments=[rule.comment_for_no_issue("tomgreef/dj-toolkit")]) == [57]


# ------------------------------------------------------------- the comments
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


def test_the_comment_for_no_issue_says_what_it_saw_why_and_what_to_do():
    text = rule.comment_for_no_issue("tomgreef/dj-toolkit")
    assert text.startswith(rule.NO_ISSUE_MARKER)
    assert "doesn't say which issue it fixes" in text
    assert "two people don't build the same thing" in text
    assert "blob/main/CONTRIBUTING.md#from-issue-to-merged-pull-request" in text
    assert "open an issue" in text and "comment there that you'd like to take it" in text
    assert "`Fixes #123`" in text
    assert "doesn't close or block" in text


def test_the_comment_for_no_issue_follows_the_voice_guide():
    text = rule.comment_for_no_issue("tomgreef/dj-toolkit").removeprefix(rule.NO_ISSUE_MARKER)
    assert text.isascii() and "!" not in text
    assert not re.search(r"\b(please|oops|whoops|unfortunately|invalid|we)\b", text, re.I)


def test_the_two_markers_are_not_the_same_or_part_of_each_other():
    assert rule.MARKER not in rule.NO_ISSUE_MARKER and rule.NO_ISSUE_MARKER not in rule.MARKER


# ------------------------------------------------------------- the glue
class FakeGitHub:
    """The `gh` command, for one pull request. Comments it is asked to post show up on the pull request. Like the real
    one, `pr view` returns only the fields it is asked for. `changed` is how many files the pull request changes in
    all, if that is more than the `files` it lists."""

    def __init__(
        self,
        author="newcomer",
        association=OUTSIDER,
        closing=(57,),
        assignees=None,
        foreign=(),
        files=("djtoolkit/settings.py",),
        changed=None,
    ):
        self.who = {"author": author, "association": association}
        self.closing = [("tomgreef", "dj-toolkit", n) for n in closing] + list(foreign)
        self.assignees = assignees or {}
        self.files = list(files)
        self.changed = len(self.files) if changed is None else changed
        self.comments: list[str] = []
        self.calls: list[tuple] = []

    def __call__(self, *args):
        self.calls.append(args)
        if args[0] == "api":
            return json.dumps(self.who)
        if args[:2] == ("pr", "view"):
            refs = [{"number": n, "repository": {"name": r, "owner": {"login": o}}} for o, r, n in self.closing]
            fields = {
                "closingIssuesReferences": refs,
                "comments": [{"body": b} for b in self.comments],
                "files": [{"path": f} for f in self.files],
                "changedFiles": self.changed,
            }
            return json.dumps({k: fields[k] for k in args[args.index("--json") + 1].split(",")})
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


def test_it_asks_which_issue_once_however_often_it_runs():
    github = FakeGitHub(closing=())
    assert "asked which one it is for" in rule.run("tomgreef/dj-toolkit", 9, github)
    assert "nothing to say" in rule.run("tomgreef/dj-toolkit", 9, github)  # a reopened pull request
    assert len(github.posted) == 1
    assert github.posted[0][2] == "9" and github.posted[0][3:5] == ("--repo", "tomgreef/dj-toolkit")
    assert rule.NO_ISSUE_MARKER in github.comments[0]
    assert not any(c[:2] == ("issue", "view") for c in github.calls)


def test_it_says_nothing_about_a_docs_only_pull_request_with_no_issue():
    github = FakeGitHub(closing=(), files=["docs/maintaining.md", "README.md"])
    assert "nothing to say" in rule.run("tomgreef/dj-toolkit", 9, github)
    assert not github.posted


def test_it_asks_when_the_files_it_was_shown_are_not_all_of_them():
    github = FakeGitHub(closing=(), files=["README.md"], changed=150)
    assert "asked which one it is for" in rule.run("tomgreef/dj-toolkit", 9, github)


def test_it_still_checks_the_assignment_of_an_issue_a_pull_request_does_name():
    github = FakeGitHub(files=["README.md"])
    assert "commented about #57" in rule.run("tomgreef/dj-toolkit", 9, github)
    assert rule.MARKER in github.comments[0] and rule.NO_ISSUE_MARKER not in github.comments[0]
