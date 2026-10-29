import os
import sys
import tempfile

if getattr(sys, "frozen", False):
    # The tempo analysis compiles with numba, which needs a writable cache folder; the app bundle isn't one.
    os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(tempfile.gettempdir(), "djtoolkit-numba"))


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    from PySide6.QtWidgets import QApplication

    from djtoolkit.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("DJ Toolkit")
    win = MainWindow()  # applies the saved theme
    win.show()
    return app.exec()


def self_test() -> int:
    """Start everything the app needs without showing a window, and exit 0 if it all works.

    The release builds run this on Windows and macOS, so a broken bundle (a missing asset, ffmpeg, the tempo
    analysis, Qt) fails the build instead of reaching a DJ. Uses a throwaway settings folder."""
    import os
    import tempfile

    os.environ["DJTOOLKIT_HOME"] = tempfile.mkdtemp(prefix="djtoolkit-selftest-")
    try:
        import numpy as np

        from djtoolkit.audio import core, export
        from djtoolkit.paths import assets_dir
        from djtoolkit.tutorials import load_tutorials

        assert load_tutorials(), "no tutorials found"
        assert (assets_dir() / "setup" / "mock" / "step1.png").is_file(), "setup images missing"

        sr, bpm = 22050, 120.0
        clicks = np.zeros((sr * 8, 1), dtype="float32")
        for k in range(16):  # a click on every beat for eight seconds
            clicks[int(k * 0.5 * sr) : int(k * 0.5 * sr) + 300] = 0.8
        found = core.detect_bpm(clicks, sr).bpm
        assert abs(found - bpm) < 2 or abs(found - bpm * 2) < 4 or abs(found - bpm / 2) < 2, f"tempo read {found}"

        out = os.path.join(os.environ["DJTOOLKIT_HOME"], "check.mp3")
        export.write_audio(__import__("pathlib").Path(out), clicks, sr, "mp3", bpm)  # also checks ffmpeg
        assert os.path.getsize(out) > 0, "mp3 export empty"

        from PySide6.QtWidgets import QApplication

        from djtoolkit.ui.main_window import MainWindow

        app = QApplication.instance() or QApplication(sys.argv)
        MainWindow().close()
        app.processEvents()
    except Exception as e:  # noqa: BLE001 - report anything
        print(f"Self-test failed: {e!r}", file=sys.stderr)
        return 1
    print("Self-test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
