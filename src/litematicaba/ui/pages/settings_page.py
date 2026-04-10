from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QWidget

from litematicaba.core.settings import AppSettings, VALID_THEMES


class SettingsPage(QWidget):
    settings_changed = Signal(AppSettings)

    def __init__(self) -> None:
        super().__init__()
        self._theme = QComboBox()
        for theme_id in VALID_THEMES:
            self._theme.addItem(theme_id, theme_id)
        self._theme.currentIndexChanged.connect(self._emit_settings)

        form = QFormLayout(self)
        form.addRow("主题", self._theme)

    def load(self, settings: AppSettings) -> None:
        idx = self._theme.findData(settings.theme_id)
        self._theme.setCurrentIndex(max(0, idx))

    def _emit_settings(self) -> None:
        self.settings_changed.emit(
            AppSettings(
                theme_id=str(self._theme.currentData()),
                sidebar_expanded=True,
                last_opened_file="",
            )
        )
