"""主界面各业务页占位（后续替换为完整实现）。"""

from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QPaintEvent, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class _HomeLogoWidget(QWidget):
    """主页 Logo：等比完整显示，不参与抬高窗口最小宽度。"""

    def __init__(self, svg_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._renderer = QSvgRenderer(svg_path, self)
        self.setMinimumSize(0, 0)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, 0)

    def sizeHint(self) -> QSize:
        return QSize(240, 56)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if not self._renderer.isValid():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        default_size = self._renderer.defaultSize()
        if default_size.height() <= 0 or default_size.width() <= 0:
            return
        aspect = default_size.width() / default_size.height()
        w = self.width()
        h = self.height()
        draw_w = min(w, int(h * aspect))
        draw_h = max(1, int(draw_w / aspect))
        if draw_h > h:
            draw_h = h
            draw_w = max(1, int(draw_h * aspect))
        x = (w - draw_w) / 2
        y = (h - draw_h) / 2
        self._renderer.render(p, QRectF(x, y, float(draw_w), float(draw_h)))


def _empty_page(title: str, hint: str) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
    t = QLabel(title)
    t.setAlignment(Qt.AlignmentFlag.AlignCenter)
    f = t.font()
    f.setPointSize(16)
    f.setBold(True)
    t.setFont(f)
    h = QLabel(hint)
    h.setAlignment(Qt.AlignmentFlag.AlignCenter)
    h.setStyleSheet("color: palette(mid);")
    lay.addWidget(t)
    lay.addWidget(h)
    return w


class HomePage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.addStretch()
        logo_path = self._logo_path()
        if logo_path is not None:
            logo = _HomeLogoWidget(str(logo_path))
            logo.setObjectName("homeLogo")
            root.addWidget(logo, 0, Qt.AlignmentFlag.AlignCenter)
        else:
            hint = QLabel("logo/bluearchive-style-logo.svg 未找到")
            hint.setStyleSheet("color: palette(mid);")
            root.addWidget(hint, 0, Qt.AlignmentFlag.AlignCenter)
        root.addStretch()

    @staticmethod
    def _logo_path() -> Path | None:
        for parent in Path(__file__).resolve().parents:
            candidate = parent / "logo" / "bluearchive-style-logo.svg"
            if candidate.is_file():
                return candidate
        return None


class LibraryPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.addWidget(_empty_page("投影库（Schematics Library）", "占位：投影文件管理将在后续实现。"))


class PropertiesPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.addWidget(_empty_page("属性（Properties）", "占位：SNBT 元数据读写将在后续实现。"))


class StatisticsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.addWidget(_empty_page("统计（Statistics）", "占位：统计分析与图表将在后续实现。"))


class FlakePage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.addWidget(_empty_page("分层（Flake）", "占位：分层平面渲染将在后续实现。"))


class RenderPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.addWidget(_empty_page("渲染（Render）", "占位：区域渲染与导出将在后续实现。"))


class ReplacePage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.addWidget(_empty_page("替换（Replace）", "占位：方块替换功能将在后续实现。"))
