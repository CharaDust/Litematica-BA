"""侧栏展开/收起：Metro 下为三横线 + 展开时粗体应用名；其它主题走标准按钮。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRect, Qt
from PySide6.QtGui import QColor, QEnterEvent, QPainter, QPen
from PySide6.QtWidgets import QApplication, QPushButton

from litematicaba.ui.theme import current_theme_id

_BG = QColor("#f7f7f7")
_BG_HOVER = QColor("#e2e2e2")
_BORDER_HOVER = QColor("#999999")
_FG = QColor("#1a1a1a")

_WIN10_SIDEBAR_THEMES = frozenset({"Metro10", "Metro8"})
_APP_TITLE = "Litematica BA"
_ICON_SLOT = 48
_HAMBURGER_PX = 16


class NavExpandButton(QPushButton):
    """Metro：三横线；展开时右侧粗体应用名。收起时仅居中显示三横线。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("navExpand")
        self.setCheckable(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setText("")  # 文案自绘
        self._sidebar_expanded = True
        self._apply_nav_theme_attrs()

    def set_sidebar_expanded(self, expanded: bool) -> None:
        self._sidebar_expanded = expanded
        self.update()

    def _use_win10_sidebar(self) -> bool:
        app = QApplication.instance()
        tid = current_theme_id(app) if app is not None else "QTDefault"
        return tid in _WIN10_SIDEBAR_THEMES

    def _apply_nav_theme_attrs(self) -> None:
        win10 = self._use_win10_sidebar()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, not win10)
        self.setMinimumHeight(48)
        self.setMaximumHeight(48)

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
    def _draw_hamburger(p: QPainter, rect: QRect) -> None:
        p.setPen(QPen(_FG, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        x1, x2 = rect.left() + 1, rect.right() - 1
        h = rect.height()
        y1 = rect.top() + h // 4
        y2 = rect.top() + h // 2
        y3 = rect.top() + 3 * h // 4
        p.drawLine(x1, y1, x2, y1)
        p.drawLine(x1, y2, x2, y2)
        p.drawLine(x1, y3, x2, y3)

    def paintEvent(self, event) -> None:
        if not self._use_win10_sidebar():
            super().paintEvent(event)
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        r = self.rect()
        hover = self.underMouse() and self.isEnabled()

        bg = _BG_HOVER if hover else _BG
        p.fillRect(r, bg)
        if hover:
            p.setPen(QPen(_BORDER_HOVER, 1))
            p.drawRect(r.adjusted(0, 0, -1, -1))

        # 三横线 16×16，置于 48×48 槽位正中（展开时槽位为左侧 48px；收起时为整行宽）
        if self._sidebar_expanded:
            hx = (_ICON_SLOT - _HAMBURGER_PX) // 2
            hy = (r.height() - _HAMBURGER_PX) // 2
            ham = QRect(hx, hy, _HAMBURGER_PX, _HAMBURGER_PX)
        else:
            hx = (r.width() - _HAMBURGER_PX) // 2
            hy = (r.height() - _HAMBURGER_PX) // 2
            ham = QRect(hx, hy, _HAMBURGER_PX, _HAMBURGER_PX)

        self._draw_hamburger(p, ham)

        if self._sidebar_expanded:
            f = self.font()
            f.setBold(True)
            p.setFont(f)
            p.setPen(_FG)
            text_rect = QRect(_ICON_SLOT, 0, max(0, r.width() - _ICON_SLOT), r.height())
            p.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, _APP_TITLE)
