"""选项页（design §2.0.4）。"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from litematicaba.core.render_bundle_update import show_renderer_update_info
from litematicaba.core.settings import VALID_THEMES, AppSettings, save_settings


class OptionsPage(QWidget):
    """主题与侧栏调试相关选项。"""

    settings_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._loading = True

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(16, 16, 16, 16)

        g_theme = QGroupBox("界面")
        form_theme = QFormLayout(g_theme)
        self._theme = QComboBox()
        for t in VALID_THEMES:
            self._theme.addItem(t, t)
        form_theme.addRow("主题：", self._theme)

        g_dev = QGroupBox("侧栏与调试")
        form_dev = QFormLayout(g_dev)
        self._show_ui_test = QCheckBox("在侧栏显示「UI 测试」入口")
        form_dev.addRow(self._show_ui_test)
        hint = QLabel("关闭后若当前在 UI 测试页，将自动返回主页。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(mid);")
        form_dev.addRow(hint)
        self._show_widget_inspector = QCheckBox("显示控件信息（悬停高亮，不拦截点击）")
        form_dev.addRow(self._show_widget_inspector)
        self._perf_test_overlay = QCheckBox("性能测试（洋红圆动画 + 左下角 FPS 浮层，均不拦截鼠标）")
        form_dev.addRow(self._perf_test_overlay)
        self._show_tile_grid = QCheckBox("显示磁贴网格（仅影响可拖拽磁贴区域）")
        form_dev.addRow(self._show_tile_grid)
        self._tile_auto_place_preferred_cols = QSpinBox()
        self._tile_auto_place_preferred_cols.setRange(1, 64)
        form_dev.addRow("自动放置磁贴优先列数：", self._tile_auto_place_preferred_cols)
        self._tile_view_right_padding_px = QSpinBox()
        self._tile_view_right_padding_px.setRange(0, 300)
        self._tile_view_right_padding_px.setSuffix(" px")
        form_dev.addRow("磁贴视图右侧留白：", self._tile_view_right_padding_px)

        g_render = QGroupBox("Deepslate 渲染")
        form_render = QFormLayout(g_render)
        hint_render = QLabel(
            "Deepslate 在构建时打入安装包，启动时不会从 GitHub 下载源码。"
            " Minecraft 方块资源缓存（若启用）与渲染包更新策略见需求文档。"
        )
        hint_render.setWordWrap(True)
        hint_render.setStyleSheet("color: palette(mid);")
        form_render.addRow(hint_render)
        self._deepslate_check_startup = QCheckBox("启动时检查渲染组件更新（需更新源可用后生效，默认关闭）")
        form_render.addRow(self._deepslate_check_startup)
        self._btn_deepslate_update = QPushButton("立即检查渲染组件更新…")
        self._btn_deepslate_update.clicked.connect(self._on_deepslate_update_clicked)
        form_render.addRow(self._btn_deepslate_update)

        body_lay.addWidget(g_theme)
        body_lay.addWidget(g_dev)
        body_lay.addWidget(g_render)
        body_lay.addStretch()

        self._theme.currentIndexChanged.connect(self._persist)
        self._show_ui_test.toggled.connect(self._persist)
        self._show_widget_inspector.toggled.connect(self._persist)
        self._perf_test_overlay.toggled.connect(self._persist)
        self._show_tile_grid.toggled.connect(self._persist)
        self._tile_auto_place_preferred_cols.valueChanged.connect(self._persist)
        self._tile_view_right_padding_px.valueChanged.connect(self._persist)
        self._deepslate_check_startup.toggled.connect(self._persist)

        self._loading = False

    def load(self, s: AppSettings) -> None:
        self._loading = True
        idx = self._theme.findData(s.theme_id)
        self._theme.setCurrentIndex(max(0, idx))
        self._show_ui_test.setChecked(s.show_ui_test_nav)
        self._show_widget_inspector.setChecked(s.show_widget_inspector)
        self._perf_test_overlay.setChecked(s.perf_test_overlay)
        self._show_tile_grid.setChecked(s.show_tile_grid)
        self._tile_auto_place_preferred_cols.setValue(s.tile_auto_place_preferred_cols)
        self._tile_view_right_padding_px.setValue(s.tile_view_right_padding_px)
        self._deepslate_check_startup.setChecked(s.deepslate_check_updates_on_startup)
        self._loading = False

    def current_settings(self) -> AppSettings:
        return AppSettings(
            theme_id=self._theme.currentData(),
            show_ui_test_nav=self._show_ui_test.isChecked(),
            show_widget_inspector=self._show_widget_inspector.isChecked(),
            show_tile_grid=self._show_tile_grid.isChecked(),
            tile_auto_place_preferred_cols=self._tile_auto_place_preferred_cols.value(),
            tile_view_right_padding_px=self._tile_view_right_padding_px.value(),
            perf_test_overlay=self._perf_test_overlay.isChecked(),
            deepslate_check_updates_on_startup=self._deepslate_check_startup.isChecked(),
        ).normalized()

    def _on_deepslate_update_clicked(self) -> None:
        show_renderer_update_info(self)

    def _persist(self) -> None:
        if self._loading:
            return
        s = self.current_settings()
        save_settings(s)
        self.settings_changed.emit(s)
