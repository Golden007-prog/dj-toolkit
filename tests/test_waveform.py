import numpy as np
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from djtoolkit.audio.align import Grid
from djtoolkit.ui.waveform import MIN_SPAN_S, RULER_H, WaveformPanel, WaveformView

SR = 44100
W = 1000


def _view(app, seconds=120.0):
    v = WaveformView()
    v.resize(W, 300)
    v.set_audio(np.random.default_rng(0).uniform(-1, 1, int(SR * seconds)).astype("float32"), SR)
    return v


def _click(v, x, y, button=Qt.MouseButton.LeftButton):
    QTest.mousePress(v, button, Qt.KeyboardModifier.NoModifier, QPoint(int(x), int(y)))


def _release(v, x, y, button=Qt.MouseButton.LeftButton):
    QTest.mouseRelease(v, button, Qt.KeyboardModifier.NoModifier, QPoint(int(x), int(y)))


def _key(v, key, mod=Qt.KeyboardModifier.NoModifier):
    QTest.keyClick(v, key, mod)


def _record(sig):
    got = []
    sig.connect(lambda *a: got.append(a))
    return got


# ------------------------------------------------------------------ view
def test_view_starts_on_the_whole_file(app):
    assert _view(app).view == (0.0, pytest.approx(120.0))


def test_zoom_keeps_the_time_under_the_cursor(app):
    v = _view(app)
    v.set_view(10.0, 30.0)
    frac = (20.0 - v.view[0]) / v.view[1]
    v.zoom(4, 20.0)
    assert v.view[1] == pytest.approx(7.5)
    assert (20.0 - v.view[0]) / v.view[1] == pytest.approx(frac)


def test_zoom_and_pan_are_clamped(app):
    v = _view(app)
    for _ in range(30):
        v.zoom(2)
    assert v.view[1] == pytest.approx(MIN_SPAN_S)
    for _ in range(30):
        v.zoom(0.5)
    assert v.view == (0.0, pytest.approx(120.0))
    v.set_view(500, 10)
    assert v.view[0] == pytest.approx(110.0)
    v.set_view(-5, 10)
    assert v.view[0] == 0.0


def test_coordinates_round_trip_while_zoomed(app):
    v = _view(app)
    v.set_view(10.0, 2.0)
    assert v.x_to_time(500) == pytest.approx(11.0)
    assert v.time_to_x(11.0) == pytest.approx(500)


def test_following_the_playhead_scrolls_it_back_into_view(app):
    v = _view(app)
    v.set_view(0.0, 10.0)
    v.set_playhead(9.8, follow=True)
    assert v.view[0] > 0 and v.view[0] <= 9.8 <= v.view[0] + v.view[1]
    v.set_view(0.0, 10.0)
    v.set_playhead(9.8, follow=False)
    assert v.view[0] == 0.0  # no follow: the view stays put


def test_every_state_paints_without_crashing(app):
    v = _view(app)
    v.set_grid(Grid(1.0, 0.5))
    v.set_beats([30.0, 30.5, 31.0, 31.5], active=1)
    v.set_cue(2.0)
    v.set_loop((30.0, 32.0))
    v.set_count_in(8)
    for step in (1, 2):
        v.set_step(step)
        for start, span in ((0, 120), (1.0, 30), (28, 6), (30, 1.0), (30.4, 0.05), (119.99, 0.05)):
            v.set_view(start, span)
            v.set_playhead(start + span / 2)
            v.grab()


# ---------------------------------------------------------------- mouse
def test_dragging_the_top_strip_scrubs(app):
    v = _view(app)
    v.set_view(10.0, 10.0)  # 100 px per second
    begin, move, end = _record(v.scrubBegin), _record(v.scrubMove), _record(v.scrubEnd)
    _click(v, 300, RULER_H - 5)
    assert begin == [(pytest.approx(13.0),)]
    QTest.mouseMove(v, QPoint(400, RULER_H - 5))
    assert move and move[-1][0] == pytest.approx(14.0)
    _release(v, 400, RULER_H - 5)
    assert len(end) == 1


def test_clicking_empty_waveform_asks_the_tab_what_to_do(app):
    v = _view(app)
    v.set_view(10.0, 10.0)
    body, pressed = _record(v.bodyClicked), _record(v.markerPressed)
    _click(v, 300, 150)
    _release(v, 300, 150)
    assert body == [(pytest.approx(13.0),)] and pressed == []


def test_grabbing_a_marker_drags_it_and_does_not_place_a_new_one(app):
    v = _view(app)
    v.set_view(10.0, 10.0)
    v.set_beats([12.0, 13.0])
    body, pressed, moved, done = (
        _record(v.bodyClicked),
        _record(v.markerPressed),
        _record(v.markerMoved),
        _record(v.dragFinished),
    )
    _click(v, 303, 150)  # within a few px of the second marker (x=300)
    assert pressed == [("beat", 1)] and body == []
    QTest.mouseMove(v, QPoint(320, 150))
    assert moved[-1][:2] == ("beat", 1) and moved[-1][2] == pytest.approx(13.2, abs=0.02)
    _release(v, 320, 150)
    assert len(done) == 1


def test_a_marker_created_by_the_click_can_be_fine_tuned_in_the_same_gesture(app):
    v = _view(app)
    v.set_view(10.0, 10.0)
    v.bodyClicked.connect(lambda t: v.set_beats([t]))  # what the tab does in step 1
    pressed = _record(v.markerPressed)
    _click(v, 300, 150)
    assert pressed == [("beat", 0)]


def test_step_two_prefers_the_start_marker_when_markers_overlap(app):
    v = _view(app)
    v.set_view(10.0, 10.0)
    v.set_beats([13.0])
    v.set_cue(13.0)
    pressed = _record(v.markerPressed)
    v.set_step(2)
    _click(v, 300, 150)
    _release(v, 300, 150)
    v.set_step(1)
    _click(v, 300, 150)
    assert pressed == [("start", 0), ("beat", 0)]


def test_right_drag_pans(app):
    v = _view(app)
    v.set_view(10.0, 10.0)
    _click(v, 500, 150, Qt.MouseButton.RightButton)
    QTest.mouseMove(v, QPoint(400, 150))
    _release(v, 400, 150, Qt.MouseButton.RightButton)
    assert v.view[0] == pytest.approx(11.0, abs=0.05)  # dragged left 100 px = 1 s later


# ------------------------------------------------------------- keyboard
def test_space_and_b_are_reported_for_the_tab(app):
    v = _view(app)
    play, tap = _record(v.togglePlay), _record(v.tapBeat)
    _key(v, Qt.Key.Key_Space)
    _key(v, Qt.Key.Key_B)
    assert len(play) == 1 and len(tap) == 1


def test_arrow_keys_nudge_only_a_selected_marker(app):
    v = _view(app)
    got = _record(v.nudgeActive)
    _key(v, Qt.Key.Key_Right)
    assert got == []  # nothing selected: nothing to nudge
    v.set_beats([5.0, 5.5])
    v.set_active("beat", 1)
    _key(v, Qt.Key.Key_Right)
    _key(v, Qt.Key.Key_Left)
    _key(v, Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)
    _key(v, Qt.Key.Key_Right, Qt.KeyboardModifier.ControlModifier)
    assert [g[0] for g in got] == [pytest.approx(0.01), pytest.approx(-0.01), pytest.approx(0.001), pytest.approx(0.1)]


def test_plus_minus_zoom(app):
    v = _view(app)
    v.set_view(0, 60)
    _key(v, Qt.Key.Key_Plus)
    assert v.view[1] < 60
    _key(v, Qt.Key.Key_Minus)
    assert v.view[1] == pytest.approx(60, rel=0.01)


def test_wheel_zooms_and_shift_wheel_pans(app):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QWheelEvent

    v = _view(app)
    v.set_view(10.0, 20.0)

    def wheel(dy, mod=Qt.KeyboardModifier.NoModifier):
        pos = QPointF(500, 150)
        v.wheelEvent(
            QWheelEvent(
                pos,
                v.mapToGlobal(pos),
                QPoint(0, 0),
                QPoint(0, dy),
                Qt.MouseButton.NoButton,
                mod,
                Qt.ScrollPhase.NoScrollPhase,
                False,
            )
        )

    wheel(120)
    assert v.view[1] < 20
    span = v.view[1]
    start = v.view[0]
    wheel(120, Qt.KeyboardModifier.ShiftModifier)
    assert v.view[1] == pytest.approx(span) and v.view[0] != start


def test_panel_scrollbar_follows_the_view(app):
    p = WaveformPanel()
    p.resize(1000, 400)
    p.set_audio(np.zeros(SR * 60, dtype="float32") + 0.1, SR)
    p.view.set_view(10.0, 20.0)
    assert p.scroll.value() == 10000 and p.scroll.pageStep() == 20000
    p.scroll.setValue(25000)
    assert p.view.view[0] == pytest.approx(25.0)
