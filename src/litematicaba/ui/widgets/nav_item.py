"""侧栏导航项：Metro10 / Metro8 下为 Win10 风格自绘；其它主题走标准 QPushButton + 主题 QSS。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QRect, QSize, Qt
from PySide6.QtGui import QColor, QEnterEvent, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QPushButton

from litematicaba.ui.theme import current_theme_id
from litematicaba.ui.themes.base import icon_dir

# 与 ``themes/sidebar_nav_win10.py`` 中侧栏色值一致
_BG = QColor("#f7f7f7")
_BG_HOVER = QColor("#e2e2e2")
_BORDER_HOVER = QColor("#999999")
_INDICATOR = QColor("#0078d7")
_TEXT = QColor("#1a1a1a")
_PLACEHOLDER_FILL = QColor("#e0e0e0")
_PLACEHOLDER_BORDER = QColor("#999999")

_WIN10_SIDEBAR_THEMES = frozenset({"Metro10", "Metro8"})

_ICON_SLOT = 48
_ICON_PX = 16
_INDICATOR_W = 4


def _resolve_nav_icon_path(icon_stem: str) -> Path:
    """``icon/<stem>.svg`` 存在则用，否则 ``icon/undefined.svg``。"""
    root = icon_dir()
    candidate = root / f"{icon_stem}.svg"
    if candidate.is_file():
        return candidate
    return root / "undefined.svg"


def _load_nav_pixmap_16(path: Path) -> QPixmap:
    pm = QIcon(str(path)).pixmap(_ICON_PX, _ICON_PX)
    if pm.isNull():
        fallback = icon_dir() / "undefined.svg"
        if fallback.is_file():
            pm = QIcon(str(fallback)).pixmap(_ICON_PX, _ICON_PX)
    return pm


class NavItemButton(QPushButton):
    """
    - **Metro10 / Metro8**：48px 高、左侧选中条、48px 图标槽与占位图；展开时左文右图标区；收起时仅居中 16×16 图标。
    - **其它主题**：普通可勾选按钮，由当前主题 QSS 绘制。
    """

    def __init__(self, full: str, short: str, *, icon_stem: str = "undefined", parent=None) -> None:
        super().__init__(full, parent)
        self.setObjectName("navItem")
        self.setCheckable(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("labelFull", full)
        self.setProperty("labelShort", short)
        self.setProperty("iconStem", icon_stem)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._nav_expanded = True
        self._nav_icon_path = _resolve_nav_icon_path(icon_stem)
        self._icon_pixmap = _load_nav_pixmap_16(self._nav_icon_path)
        self.setIcon(QIcon(str(self._nav_icon_path)))
        self.setIconSize(QSize(_ICON_PX, _ICON_PX))
        self._apply_nav_theme_attrs()

    def set_nav_expanded(self, expanded: bool) -> None:
        self._nav_expanded = expanded
        self.update()

    def _use_win10_sidebar(self) -> bool:
        app = QApplication.instance()
        tid = current_theme_id(app) if app is not None else "QTDefault"
        return tid in _WIN10_SIDEBAR_THEMES

    def _apply_nav_theme_attrs(self) -> None:
        win10 = self._use_win10_sidebar()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, not win10)
        if win10:
            self.setFixedHeight(48)
        else:
            self.setMinimumHeight(32)
            self.setMaximumHeight(16777215)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.StyleChange:
            self._apply_nav_theme_attrs()
            self.update()
        super().changeEvent(event)

    def enterEvent(self, event: QEnterEvent) -> None:
        super().enterEvent(event)
        if self._use_win10_sidebar():
            self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        if self._use_win10_sidebar():
            self.update()

    @staticmethod
    def _draw_placeholder_icon(p: QPainter, rect: QRect) -> None:
        p.setPen(QPen(_PLACEHOLDER_BORDER, 1))
        p.setBrush(_PLACEHOLDER_FILL)
        p.drawRoundedRect(rect.adjusted(0, 0, -1, -1), 2, 2)

    def _draw_nav_icon(self, p: QPainter, rect: QRect) -> None:
        if not self._icon_pixmap.isNull():
            p.drawPixmap(rect, self._icon_pixmap)
        else:
            self._draw_placeholder_icon(p, rect)

    def paintEvent(self, event) -> None:
        if not self._use_win10_sidebar():
            super().paintEvent(event)
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        r = self.rect()
        hover = self.underMouse() and self.isEnabled()
        checked = self.isChecked()

        bg = _BG_HOVER if hover else _BG
        p.fillRect(r, bg)

        if hover:
            p.setPen(QPen(_BORDER_HOVER, 1))
            p.drawRect(r.adjusted(0, 0, -1, -1))

        if self._nav_expanded:
            # 图标槽 [0,48)，文案紧随其后；布局不因选中条改变
            slot = QRect(0, 0, _ICON_SLOT, r.height())
            icon_rect = QRect(0, 0, _ICON_PX, _ICON_PX)
            icon_rect.moveCenter(slot.center())
            self._draw_nav_icon(p, icon_rect)

            label = str(self.property("labelFull") or self.text())
            f = self.font()
            p.setFont(f)
            p.setPen(_TEXT)
            text_left = _ICON_SLOT
            text_rect = QRect(text_left, 0, max(0, r.width() - text_left), r.height())
            p.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
        else:
            # 收起：整行宽度内居中 16×16（不预留指示条宽度）
            slot = QRect(0, 0, r.width(), r.height())
            icon_rect = QRect(0, 0, _ICON_PX, _ICON_PX)
            icon_rect.moveCenter(slot.center())
            self._draw_nav_icon(p, icon_rect)

        # 选中条最后绘制，叠在底层内容之上，不占布局宽度
        if checked:
            h_ind = 24
            y0 = (r.height() - h_ind) // 2
            p.fillRect(QRect(0, y0, _INDICATOR_W, h_ind), _INDICATOR)
