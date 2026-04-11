from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class HomePage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("LitematicaBA (Qt 重构版)"))
        layout.addWidget(QLabel("这里作为主页/项目状态入口。"))
        layout.addStretch()
