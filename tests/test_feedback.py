"""Requests: reading the most-voted ideas from GitHub, and the page that shows them. No network: GitHub is faked."""

from urllib.parse import parse_qs, urlparse

import pytest
import requests

from djtoolkit import __version__, feedback
from djtoolkit.feedback import FeedbackUnavailable, Idea


class FakeResponse:
    def __init__(self, status=200, items=()):
        self.status_code = status
        self.ok = status < 400
        self._items = list(items)

    def json(self):
        return {"items": self._items}


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


def _item(n, title, votes):
    return {"number": n, "title": title, "html_url": f"https://github.com/x/y/issues/{n}", "reactions": {"+1": votes}}


def test_ideas_come_back_most_voted_first_and_ties_oldest_first():
    s = FakeSession(FakeResponse(items=[_item(3, "C", 1), _item(1, "A", 5), _item(2, "B", 1), _item(4, "D", 0)]))
    ideas = feedback.top_ideas(limit=3, session=s)
    assert [(i.number, i.votes) for i in ideas] == [(1, 5), (2, 1), (3, 1)]
    url, kw = s.calls[0]
    assert url == feedback.SEARCH_URL and "label:idea" in kw["params"]["q"] and "is:open" in kw["params"]["q"]
    assert kw["params"]["sort"] == "reactions-+1" and kw["timeout"]


def test_an_issue_without_reactions_counts_as_no_votes():
    item = _item(7, "New", 0)
    del item["reactions"]
    assert feedback.top_ideas(session=FakeSession(FakeResponse(items=[item]))) == [Idea(7, "New", 0, item["html_url"])]


@pytest.mark.parametrize(
    ("session", "says"),
    [
        (FakeSession(error=requests.ConnectionError("down")), "Check your connection"),
        (FakeSession(FakeResponse(status=403)), "busy"),
        (FakeSession(FakeResponse(status=500)), "didn't answer"),
    ],
)
def test_problems_become_a_calm_message(session, says):
    with pytest.raises(FeedbackUnavailable, match=says):
        feedback.top_ideas(session=session)


def test_the_forms_open_on_the_right_template_with_the_version_filled_in():
    q = parse_qs(urlparse(feedback.bug_url()).query)
    assert (
        q["template"] == ["bug_report.yml"] and q["version"] == [__version__] and q["system"][0]
    )  # ids in bug_report.yml
    assert parse_qs(urlparse(feedback.suggest_url()).query)["template"] == ["idea.yml"]
    assert feedback.bug_url().startswith(feedback.REPO_URL + "/issues/new?")


# ------------------------------------------------------------------ the page
@pytest.fixture
def page(app):
    from djtoolkit.ui.requests_tab import RequestsTab

    opened = []
    ideas = [
        Idea(1, "Detect the key of an acapella", 4, "https://x/1"),
        Idea(2, "A gig-ready USB check", 2, "https://x/2"),
    ]
    tab = RequestsTab(fetch=lambda: ideas, opener=opened.append)
    tab.opened = opened
    return tab


def test_the_page_lists_the_ideas_with_their_votes(page):
    page.load_now()
    assert [i.title for i in page.ideas] == ["Detect the key of an acapella", "A gig-ready USB check"]
    assert "Sorted by votes" in page.status.text() and not page.retry_btn.isVisible()


def test_voting_suggesting_and_reporting_open_github(page):
    from PySide6.QtWidgets import QPushButton

    page.load_now()
    votes = [b for b in page.findChildren(QPushButton) if b.text() == "Vote"]
    votes[1].click()
    page.suggest_btn.click()
    page.bug_btn.click()
    assert page.opened[0] == "https://x/2"
    assert "template=idea.yml" in page.opened[1] and "template=bug_report.yml" in page.opened[2]


def test_offline_shows_a_way_forward_not_an_error(app):
    from djtoolkit.ui.requests_tab import RequestsTab

    def offline():
        raise FeedbackUnavailable("Couldn't reach GitHub. Check your connection, then try again.")

    tab = RequestsTab(fetch=offline, opener=lambda _u: None)
    tab.load_now()
    assert "Check your connection" in tab.status.text() and not tab.retry_btn.isHidden()


def test_an_empty_list_invites_the_first_idea(app):
    from djtoolkit.ui.requests_tab import RequestsTab

    tab = RequestsTab(fetch=lambda: [], opener=lambda _u: None)
    tab.load_now()
    assert "Suggest the first one" in tab.status.text()


def test_nothing_is_fetched_until_the_page_is_opened(app):
    from djtoolkit.ui.main_window import MainWindow

    calls = []
    w = MainWindow()
    w.requests._fetch = lambda: calls.append(1) or []
    w.go(0)
    assert calls == []  # opening the app doesn't reach out to GitHub
    w.close()


def test_tests_cannot_reach_the_network():
    with pytest.raises(AssertionError, match="network"):
        requests.get("https://example.com", timeout=1)


def test_the_app_only_prefills_fields_the_github_forms_have():
    """Rename a field in .github/ISSUE_TEMPLATE and the app's pre-filled links would silently stop working."""
    import re
    from pathlib import Path

    forms = Path(__file__).resolve().parents[1] / ".github" / "ISSUE_TEMPLATE"
    for url in (feedback.bug_url(), feedback.suggest_url()):
        query = parse_qs(urlparse(url).query)
        form = forms / query.pop("template")[0]
        assert form.is_file(), form.name
        ids = set(re.findall(r"^\s+id: (\w+)\s*$", form.read_text("utf8"), re.M))
        assert set(query) <= ids, f"{form.name} has no field {set(query) - ids}"
