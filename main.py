import sys

from PySide6.QtWidgets import QApplication

from djtoolkit.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("DJ Toolkit")
    win = MainWindow()  # applies the saved theme
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
