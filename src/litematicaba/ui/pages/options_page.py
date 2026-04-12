"""选项页（design §2.0.4）。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from litematicaba.core.config import user_data_dir
from litematicaba.core.render_bundle_update import show_renderer_update_info
from litematicaba.core.settings import VALID_THEMES, AppSettings, save_settings
from litematicaba.ui.mcmeta_version_picker_dialog import McmetaVersionPickerDialog


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
        self._deepslate_invert_y = QCheckBox(
            "3D 视图反转纵向拖拽（触摸屏与鼠标纵向习惯相反时勾选；未勾选为常见鼠标习惯）"
        )
        form_render.addRow(self._deepslate_invert_y)
        self._deepslate_check_startup = QCheckBox("启动时检查渲染组件更新（需更新源可用后生效，默认关闭）")
        form_render.addRow(self._deepslate_check_startup)
        self._btn_deepslate_update = QPushButton("立即检查渲染组件更新…")
        self._btn_deepslate_update.clicked.connect(self._on_deepslate_update_clicked)
        form_render.addRow(self._btn_deepslate_update)

        g_nbt = QGroupBox("NBT 3D 预览 — 游戏资源（mcmeta）")
        form_nbt = QFormLayout(g_nbt)
        hint_nbt = QLabel(
            "与 Minecraft 数据版本相关的方块定义、模型与图集按版本分目录保存在用户数据下，不随应用安装包更新。"
            " 在管理窗口中下载后需点击「应用」才会用于 3D 预览；更新 NBT Viewer 前端（editor.js）仍请使用仓库内 tools/build_nbt_viewer.ps1。"
        )
        hint_nbt.setWordWrap(True)
        hint_nbt.setStyleSheet("color: palette(mid);")
        form_nbt.addRow(hint_nbt)
        self._lbl_nbt_mcmeta_status = QLabel("—")
        self._lbl_nbt_mcmeta_status.setWordWrap(True)
        form_nbt.addRow("当前 mcmeta：", self._lbl_nbt_mcmeta_status)
        self._btn_nbt_fetch = QPushButton("管理游戏资源版本…")
        self._btn_nbt_fetch.clicked.connect(self._on_nbt_manage_clicked)
        form_nbt.addRow(self._btn_nbt_fetch)
        self._nbt_mcmeta_last_choice = ""

        body_lay.addWidget(g_theme)
        body_lay.addWidget(g_dev)
        body_lay.addWidget(g_render)
        body_lay.addWidget(g_nbt)
        body_lay.addStretch()

        self._theme.currentIndexChanged.connect(self._persist)
        self._show_ui_test.toggled.connect(self._persist)
        self._show_widget_inspector.toggled.connect(self._persist)
        self._perf_test_overlay.toggled.connect(self._persist)
        self._show_tile_grid.toggled.connect(self._persist)
        self._tile_auto_place_preferred_cols.valueChanged.connect(self._persist)
        self._tile_view_right_padding_px.valueChanged.connect(self._persist)
        self._deepslate_invert_y.toggled.connect(self._persist)
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
        self._deepslate_invert_y.setChecked(s.deepslate_invert_y)
        self._deepslate_check_startup.setChecked(s.deepslate_check_updates_on_startup)
        self._nbt_mcmeta_last_choice = s.nbt_mcmeta_target_version
        self._refresh_nbt_mcmeta_status_label()
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
            deepslate_invert_y=self._deepslate_invert_y.isChecked(),
            nbt_mcmeta_target_version=self._nbt_mcmeta_last_choice.strip(),
        ).normalized()

    def _on_deepslate_update_clicked(self) -> None:
        show_renderer_update_info(self)

    def _nbt_assets_base_dir(self) -> Path:
        return user_data_dir() / "minecraft-assets" / "nbt-viewer"

    def _refresh_nbt_mcmeta_status_label(self) -> None:
        base = self._nbt_assets_base_dir()
        applied = self._nbt_mcmeta_last_choice.strip()
        if applied:
            ver_file = base / applied / "mcmeta" / "version.txt"
            if ver_file.is_file():
                try:
                    v = ver_file.read_text(encoding="utf-8").strip()
                    self._lbl_nbt_mcmeta_status.setText(
                        f"当前应用：{applied}（mcmeta 记录 {v}）\n{ver_file.parent}"
                    )
                except OSError:
                    self._lbl_nbt_mcmeta_status.setText(f"无法读取：{ver_file}")
            else:
                self._lbl_nbt_mcmeta_status.setText(
                    f"已选择应用「{applied}」，但该版本资源未下载或不完整。\n预期目录：{base / applied / 'mcmeta'}"
                )
            return
        legacy = base / "mcmeta" / "version.txt"
        if legacy.is_file():
            try:
                v = legacy.read_text(encoding="utf-8").strip()
                self._lbl_nbt_mcmeta_status.setText(
                    f"未指定应用版本；将使用旧版单层 mcmeta（{v}）。\n{legacy.parent}\n"
                    "建议在管理窗口中选择版本并点击「应用」。"
                )
            except OSError:
                self._lbl_nbt_mcmeta_status.setText(f"无法读取：{legacy}")
            return
        self._lbl_nbt_mcmeta_status.setText(
            f"未选择应用版本且无旧版 mcmeta。\n根目录：{base}\n"
            "请打开「管理游戏资源版本」下载资源，并点击对应行的「应用」。"
        )

    def _on_nbt_manage_clicked(self) -> None:
        dlg = McmetaVersionPickerDialog(
            self._nbt_assets_base_dir(),
            self._nbt_mcmeta_last_choice.strip(),
            self,
        )
        dlg.apply_requested.connect(self._on_nbt_apply_version_from_dialog)
        dlg.library_changed.connect(self._refresh_nbt_mcmeta_status_label)
        dlg.exec()

    def _on_nbt_apply_version_from_dialog(self, version_id: str) -> None:
        self._nbt_mcmeta_last_choice = (version_id or "").strip()
        self._persist()
        self._refresh_nbt_mcmeta_status_label()

    def _persist(self) -> None:
        if self._loading:
            return
        s = self.current_settings()
        save_settings(s)
        self.settings_changed.emit(s)
