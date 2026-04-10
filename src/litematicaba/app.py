from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from litematicaba.core.settings import load_settings
from litematicaba.ui.main_window import MainWindow
from litematicaba.ui.theme import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    settings = load_settings()
    apply_theme(app, settings.theme_id)

    window = MainWindow()
    window.show()
    return app.exec()
