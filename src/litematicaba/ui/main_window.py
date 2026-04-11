"""主窗口：左侧导航 + 右侧堆叠页面（design §2.0）。"""

from __future__ import annotations

from PySide6.QtGui import QGuiApplication, QResizeEvent, QShowEvent
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from litematicaba.core.settings import AppSettings, load_settings
from litematicaba.ui.pages import (
    FlakePage,
    HomePage,
    LibraryPage,
    OptionsPage,
    PropertiesPage,
    RenderPage,
    ReplacePage,
    StatisticsPage,
    UiTestPage,
)
from litematicaba.ui.theme import apply_theme, current_theme_id
from litematicaba.ui.widget_inspector import WidgetInspectorController
from litematicaba.ui.widgets.nav_expand import NavExpandButton
from litematicaba.ui.widgets.nav_item import NavItemButton

PAGE_HOME = 0
PAGE_LIBRARY = 1
PAGE_PROPERTIES = 2
PAGE_STATISTICS = 3
PAGE_FLAKE = 4
PAGE_RENDER = 5
PAGE_REPLACE = 6
PAGE_UI_TEST = 7
PAGE_OPTIONS = 8


class MainWindow(QWidget):
    """使用 QWidget 作顶层容器，便于与 QSS 背景一致；标题栏由系统装饰。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LitematicaBA")
        self.resize(960, 600)

        self._settings = load_settings()
        apply_theme(QApplication.instance(), self._settings.theme_id)

        self._sidebar_expanded = True
        self._sidebar_width_expanded = 220
        self._sidebar_width_collapsed = 48

        self._stack = QStackedWidget()
        self._stack.addWidget(HomePage())
        self._stack.addWidget(LibraryPage())
        self._properties_page = PropertiesPage()
        self._stack.addWidget(self._properties_page)
        self._statistics_page = StatisticsPage(self._properties_page)
        self._stack.addWidget(self._statistics_page)
        self._stack.addWidget(FlakePage())
        self._stack.addWidget(RenderPage())
        self._stack.addWidget(ReplacePage())
        self._ui_test_page = UiTestPage(
            show_tile_grid=self._settings.show_tile_grid,
            theme_id=self._settings.theme_id,
            tile_auto_place_preferred_cols=self._settings.tile_auto_place_preferred_cols,
            tile_view_right_padding_px=self._settings.tile_view_right_padding_px,
        )
        self._stack.addWidget(self._ui_test_page)
        self._options_page = OptionsPage()
        self._stack.addWidget(self._options_page)
        self._options_page.load(self._settings)
        self._options_page.settings_changed.connect(self._on_settings_changed)
        self._ui_test_page.apply_settings(self._settings)

        self._expand_btn = NavExpandButton()
        self._expand_btn.setToolTip("收起侧栏")
        self._expand_btn.clicked.connect(self._toggle_sidebar)

        # icon_stem 对应 ``ui/resources/icon/<stem>.svg``，缺省则用 undefined.svg
        self._btn_home = NavItemButton("主页", "主", icon_stem="home")
        self._btn_library = NavItemButton("投影库", "库", icon_stem="gallery")
        self._btn_properties = NavItemButton("属性", "属", icon_stem="properties")
        self._btn_statistics = NavItemButton("统计", "统", icon_stem="statistics")
        self._btn_flake = NavItemButton("分层", "层", icon_stem="flake")
        self._btn_render = NavItemButton("渲染", "染", icon_stem="render")
        self._btn_replace = NavItemButton("替换", "替", icon_stem="replace")
        self._btn_ui_test = NavItemButton("UI 测试", "测", icon_stem="ui_debug")
        self._btn_options = NavItemButton("选项", "项", icon_stem="options")

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        for b in (
            self._btn_home,
            self._btn_library,
            self._btn_properties,
            self._btn_statistics,
            self._btn_flake,
            self._btn_render,
            self._btn_replace,
            self._btn_ui_test,
            self._btn_options,
        ):
            self._btn_group.addButton(b)

        self._btn_home.clicked.connect(lambda: self._stack.setCurrentIndex(PAGE_HOME))
        self._btn_library.clicked.connect(lambda: self._stack.setCurrentIndex(PAGE_LIBRARY))
        self._btn_properties.clicked.connect(self._on_nav_properties)
        self._btn_statistics.clicked.connect(lambda: self._stack.setCurrentIndex(PAGE_STATISTICS))
        self._btn_flake.clicked.connect(lambda: self._stack.setCurrentIndex(PAGE_FLAKE))
        self._btn_render.clicked.connect(lambda: self._stack.setCurrentIndex(PAGE_RENDER))
        self._btn_replace.clicked.connect(lambda: self._stack.setCurrentIndex(PAGE_REPLACE))
        self._btn_ui_test.clicked.connect(lambda: self._stack.setCurrentIndex(PAGE_UI_TEST))
        self._btn_options.clicked.connect(lambda: self._stack.setCurrentIndex(PAGE_OPTIONS))

        self._stack.currentChanged.connect(self._sync_nav_checks)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setFrameShadow(QFrame.Shadow.Plain)
        sep1.setFixedHeight(1)
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFrameShadow(QFrame.Shadow.Plain)
        sep2.setFixedHeight(1)

        side = QWidget()
        side.setObjectName("navSidebar")
        side_l = QVBoxLayout(side)
        # Win10：相邻导航项无竖向间隙（分隔线仍占位 1px）
        side_l.setSpacing(0)
        side_l.setContentsMargins(0, 0, 0, 0)
        side_l.addWidget(self._expand_btn)
        side_l.addWidget(self._btn_home)
        side_l.addWidget(sep1)
        side_l.addWidget(self._btn_library)
        side_l.addWidget(self._btn_properties)
        side_l.addWidget(self._btn_statistics)
        side_l.addWidget(self._btn_flake)
        side_l.addWidget(self._btn_render)
        side_l.addWidget(self._btn_replace)
        side_l.addWidget(sep2)
        side_l.addStretch()
        side_l.addWidget(self._btn_ui_test)
        side_l.addWidget(self._btn_options)

        root = QHBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(side)
        root.addWidget(self._stack, 1)

        self._nav_sidebar = side
        self._btn_ui_test.setVisible(self._settings.show_ui_test_nav)
        self._apply_sidebar_geometry()
        self._widget_inspector = WidgetInspectorController(self)
        self._widget_inspector.set_enabled(self._settings.show_widget_inspector)
        self._btn_home.setChecked(True)
        self._stack.setCurrentIndex(PAGE_HOME)

        # 避免子控件（如主页 Logo）曾出现过大 minimumSize 后把整窗最小宽度锁死
        self.setMinimumSize(0, 0)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._widget_inspector.sync_geometry()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._widget_inspector.sync_geometry()
        self._clamp_window_to_available_geometry()

    def _clamp_window_to_available_geometry(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        ag = screen.availableGeometry()
        nw = min(self.width(), max(320, ag.width()))
        nh = min(self.height(), max(240, ag.height()))
        if nw < self.width() or nh < self.height():
            self.resize(nw, nh)
        fg = self.frameGeometry()
        if not ag.contains(fg):
            x = max(ag.left(), min(fg.left(), ag.right() - fg.width()))
            y = max(ag.top(), min(fg.top(), ag.bottom() - fg.height()))
            self.move(x, y)

    def _toggle_sidebar(self) -> None:
        self._sidebar_expanded = not self._sidebar_expanded
        self._apply_sidebar_geometry()

    def _apply_sidebar_geometry(self) -> None:
        w = self._sidebar_width_expanded if self._sidebar_expanded else self._sidebar_width_collapsed
        self._nav_sidebar.setFixedWidth(w)
        app = QApplication.instance()
        tid = current_theme_id(app) if app is not None else "QTDefault"
        metro_nav = tid in ("Metro10", "Metro8")

        if self._sidebar_expanded:
            self._expand_btn.setToolTip("收起侧栏")
        else:
            self._expand_btn.setToolTip("展开侧栏")

        if metro_nav:
            self._expand_btn.setText("")
            self._expand_btn.set_sidebar_expanded(self._sidebar_expanded)
        else:
            self._expand_btn.setText("«" if self._sidebar_expanded else "»")

        for b in self._btn_group.buttons():
            full = b.property("labelFull") or ""
            short = b.property("labelShort") or ""
            b.setText(full if self._sidebar_expanded else short)
            b.set_nav_expanded(self._sidebar_expanded)
            if not self._sidebar_expanded:
                b.setToolTip(str(full))
            else:
                b.setToolTip("")

    def _sync_nav_checks(self, index: int) -> None:
        mapping = {
            PAGE_HOME: self._btn_home,
            PAGE_LIBRARY: self._btn_library,
            PAGE_PROPERTIES: self._btn_properties,
            PAGE_STATISTICS: self._btn_statistics,
            PAGE_FLAKE: self._btn_flake,
            PAGE_RENDER: self._btn_render,
            PAGE_REPLACE: self._btn_replace,
            PAGE_UI_TEST: self._btn_ui_test,
            PAGE_OPTIONS: self._btn_options,
        }
        btn = mapping.get(index)
        if btn is None:
            return
        self._btn_group.setExclusive(False)
        btn.setChecked(True)
        for other in self._btn_group.buttons():
            if other is not btn:
                other.setChecked(False)
        self._btn_group.setExclusive(True)

    def _on_nav_properties(self) -> None:
        self._properties_page.apply_regions_table_theme()
        self._stack.setCurrentIndex(PAGE_PROPERTIES)

    def _on_settings_changed(self, s: AppSettings) -> None:
        self._settings = s
        apply_theme(QApplication.instance(), s.theme_id)
        self._btn_ui_test.setVisible(s.show_ui_test_nav)
        self._widget_inspector.set_enabled(s.show_widget_inspector)
        self._ui_test_page.apply_settings(s)
        self._properties_page.apply_regions_table_theme()
        self._apply_sidebar_geometry()
        if not s.show_ui_test_nav and self._stack.currentIndex() == PAGE_UI_TEST:
            self._stack.setCurrentIndex(PAGE_HOME)
