"""Every mode + accent combination must stay readable. Edit a palette, run this, and it tells you what broke."""

import pytest

from djtoolkit.ui import theme

COMBOS = [(m, a) for m in ("dark", "light") for a in theme.ACCENTS]


def _id(c):
    return f"{c[0]}-{c[1]}"


@pytest.fixture(params=COMBOS, ids=_id)
def p(request):
    return theme.palette(*request.param)


def test_text_pairs_meet_4_5(p):
    surfaces = [p.bg, p.sidebar, p.panel, p.panel2, p.hover, p.select]
    bad = []
    for fg_name in ("text", "muted"):
        for s in surfaces:
            r = theme.contrast(getattr(p, fg_name), s)
            if r < 4.5:
                bad.append((fg_name, s, round(r, 2)))
    for fg_name in ("link", "danger", "success", "warn"):
        for s in (p.bg, p.sidebar, p.panel, p.panel2):
            r = theme.contrast(getattr(p, fg_name), s)
            if r < 4.5:
                bad.append((fg_name, s, round(r, 2)))
    for a, b in (
        (p.on_primary, p.primary),
        (p.on_primary, p.primary_hover),
        (p.on_cue, p.cue),
        (p.on_stage, p.stage_link),
    ):
        r = theme.contrast(a, b)
        if r < 4.5:
            bad.append((a, b, round(r, 2)))
    for fg_name in ("stage_text", "stage_muted", "stage_link"):  # text drawn on the waveform stage
        for s in (p.stage, p.stage_raised):
            r = theme.contrast(getattr(p, fg_name), s)
            if r < 4.5:
                bad.append((fg_name, s, round(r, 2)))
    assert not bad, bad


def test_non_text_pairs_meet_3(p):
    """WCAG 1.4.11: control outlines and the marks that carry information need 3:1."""
    bad = []
    for fg_name, surfaces in (
        ("border_strong", (p.panel, p.panel2, p.bg)),  # input outlines
        ("primary", (p.panel,)),  # the filled primary button against the card it sits on
        ("cue", (p.panel, p.stage)),  # the downbeat marker, on a card and on the stage
        ("stage_data", (p.stage,)),  # waveform ink
        ("stage_link", (p.stage,)),  # beat markers
    ):
        for s in surfaces:
            r = theme.contrast(getattr(p, fg_name), s)
            if r < 3.0:
                bad.append((fg_name, s, round(r, 2)))
    assert not bad, bad


def test_the_accent_is_the_only_hue_that_changes():
    a, b = theme.palette("dark", "violet"), theme.palette("dark", "rose")
    assert (a.bg, a.panel, a.text, a.cue, a.danger) == (b.bg, b.panel, b.text, b.cue, b.danger)
    assert a.primary != b.primary and a.stage_link != b.stage_link


def test_unknown_mode_or_accent_falls_back_safely():
    assert (
        theme.palette("nonsense", "nope").name == "dark"
        and theme.palette("light", "nope").accent == theme.DEFAULT_ACCENT
    )


def test_the_stage_is_dark_in_both_modes():
    for mode in ("dark", "light"):
        pal = theme.palette(mode)
        assert theme._lum(pal.stage) < 0.02 and theme._lum(pal.stage_text) > 0.5


def test_stylesheet_is_fully_resolved(p):
    css = theme.stylesheet(p, "x.png")
    assert "None" not in css and "Palette(" not in css
    assert "{c." not in css and "{{" not in css and "}}" not in css
    assert p.primary in css and p.border_strong in css


def test_subscribers_are_notified():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    calls = []
    theme.subscribe(lambda: calls.append((theme.P.name, theme.P.accent)))
    theme.apply(app, "light", "rose")
    theme.apply(app, "dark", "blue")
    assert calls[-2:] == [("light", "rose"), ("dark", "blue")]
