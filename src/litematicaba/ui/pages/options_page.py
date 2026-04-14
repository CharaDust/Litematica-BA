"""选项页（design §2.0.4）。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
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
from litematicaba.core.material_list_icon_pixmap_cache import material_list_icon_prewarm_cache_has_entries
from litematicaba.core.settings import (
    BLOCK_ICON_PRELOAD_NEVER,
    BLOCK_ICON_PRELOAD_ON_LITEMATIC,
    BLOCK_ICON_PRELOAD_ON_MATERIAL_OR_FLAKE,
    BLOCK_ICON_PRELOAD_STARTUP,
    DEFAULT_BLOCK_ICON_PRELOAD_MODE,
    MATERIAL_LIST_PREWARM_ON_LITEMATIC,
    MATERIAL_LIST_PREWARM_ON_MATERIAL_LIST,
    NBT_EXPORT_FULL_MARGIN_DEFAULT,
    NBT_EXPORT_FULL_ORTHOGRAPHIC_DIAG_EXTRA_DEFAULT,
    NBT_EXPORT_FULL_ORTHOGRAPHIC_HALF_HEIGHT_MIN_DEFAULT,
    NBT_EXPORT_FULL_ORTHOGRAPHIC_HEIGHT_SCALE_DEFAULT,
    NBT_EXPORT_FULL_ORTHOGRAPHIC_MIN_DISTANCE_DEFAULT,
    NBT_EXPORT_FULL_ORTHOGRAPHIC_NEED_HALF_PADDING_DEFAULT,
    NBT_EXPORT_FULL_PERSPECTIVE_DIAG_EXTRA_DEFAULT,
    NBT_EXPORT_FULL_PERSPECTIVE_MIN_DISTANCE_DEFAULT,
    NBT_VIEWER_LARGE_STRUCTURE_THRESHOLD_DEFAULT,
    VALID_THEMES,
    AppSettings,
    save_settings,
)
from litematicaba.ui.game_resource_block_icon_dialog import GameResourceBlockIconDialog
from litematicaba.ui.game_resource_language_dialog import GameResourceLanguageDialog
from litematicaba.ui.mcmeta_version_picker_dialog import McmetaVersionPickerDialog


class OptionsPage(QWidget):
    """主题与侧栏调试相关选项。"""

    settings_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._loading = True
        self._committed_block_icon_mode = DEFAULT_BLOCK_ICON_PRELOAD_MODE

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

        g_perf = QGroupBox("性能与预加载")
        form_perf = QFormLayout(g_perf)
        perf_hint = QLabel(
            "更改以下选项不会清除已缓存的材料列表磁盘数据，也不会清除已解码的方块图标内存；"
            "切换「应用到材料列表」的图标包时仍会按规则使图标缓存失效。"
        )
        perf_hint.setWordWrap(True)
        perf_hint.setStyleSheet("color: palette(mid);")
        form_perf.addRow(perf_hint)
        self._block_icon_preload = QComboBox()
        self._block_icon_preload.addItem("软件启动时（默认）", BLOCK_ICON_PRELOAD_STARTUP)
        self._block_icon_preload.addItem("首次加载投影文件时", BLOCK_ICON_PRELOAD_ON_LITEMATIC)
        self._block_icon_preload.addItem("首次点击材料列表或分层时", BLOCK_ICON_PRELOAD_ON_MATERIAL_OR_FLAKE)
        self._block_icon_preload.addItem("不加载方块图标（回退手段）", BLOCK_ICON_PRELOAD_NEVER)
        form_perf.addRow("方块图标预加载时机：", self._block_icon_preload)
        self._material_list_prewarm = QComboBox()
        self._material_list_prewarm.addItem(
            "首次加载投影文件时（默认）", MATERIAL_LIST_PREWARM_ON_LITEMATIC
        )
        self._material_list_prewarm.addItem(
            "首次点击材料列表时", MATERIAL_LIST_PREWARM_ON_MATERIAL_LIST
        )
        form_perf.addRow("材料列表计算时机：", self._material_list_prewarm)

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
        self._btn_deepslate_update = QPushButton("立即检查渲染组件更新...")
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
        self._btn_nbt_fetch = QPushButton("管理游戏资源...")
        self._btn_nbt_fetch.clicked.connect(self._on_nbt_manage_clicked)
        form_nbt.addRow(self._btn_nbt_fetch)
        self._btn_lang_manage = QPushButton("管理游戏语言...")
        self._btn_lang_manage.clicked.connect(self._on_lang_manage_clicked)
        form_nbt.addRow(self._btn_lang_manage)
        self._btn_block_icon_manage = QPushButton("管理方块图标...")
        self._btn_block_icon_manage.clicked.connect(self._on_block_icon_manage_clicked)
        form_nbt.addRow(self._btn_block_icon_manage)
        self._nbt_viewer_camera_debug = QCheckBox(
            "在 NBT 3D 预览中显示相机调试信息（cPos、cRot、与目标距离 cDist、结构尺寸等）"
        )
        form_nbt.addRow(self._nbt_viewer_camera_debug)
        self._nbt_large_structure_threshold = QSpinBox()
        self._nbt_large_structure_threshold.setRange(1_000, 1_000_000_000)
        self._nbt_large_structure_threshold.setSingleStep(1_000)
        self._nbt_large_structure_threshold.setToolTip(
            "当结构体积（x*y*z）超过此值时，显示“Trying to render a very large structure”确认提示。"
            f"默认值：{NBT_VIEWER_LARGE_STRUCTURE_THRESHOLD_DEFAULT}（48×48×48）。"
        )
        form_nbt.addRow("大结构提示阈值（体素）：", self._nbt_large_structure_threshold)
        self._nbt_mcmeta_last_choice = ""

        g_nbt_export = QGroupBox("NBT 3D — 完整入镜导出（「导出…」）")
        form_exp = QFormLayout(g_nbt_export)
        hint_exp = QLabel(
            "以下参数用于在保持当前画布分辨率与旋转（cRot）的前提下，估算相机距离使结构整体入镜；"
            "透视（FOV>0°）与正交（FOV=0°）使用不同公式。提示中的数值为应用内置默认值。"
        )
        hint_exp.setWordWrap(True)
        hint_exp.setStyleSheet("color: palette(mid);")
        form_exp.addRow(hint_exp)

        self._nbt_export_margin = QDoubleSpinBox()
        self._nbt_export_margin.setRange(1.001, 3.0)
        self._nbt_export_margin.setDecimals(3)
        self._nbt_export_margin.setSingleStep(0.01)
        self._nbt_export_margin.setToolTip(
            f"等效包围半径 r = 对角线半长 × 本系数；>1 增加留白。默认值：{NBT_EXPORT_FULL_MARGIN_DEFAULT}。"
        )
        form_exp.addRow("共用 · 入镜边距系数：", self._nbt_export_margin)

        self._nbt_export_persp_min = QDoubleSpinBox()
        self._nbt_export_persp_min.setRange(0.5, 500.0)
        self._nbt_export_persp_min.setDecimals(3)
        self._nbt_export_persp_min.setSingleStep(0.5)
        self._nbt_export_persp_min.setToolTip(
            f"透视模式下相机距离下限（方块单位）。默认值：{NBT_EXPORT_FULL_PERSPECTIVE_MIN_DISTANCE_DEFAULT}。"
        )
        form_exp.addRow("透视 · 最小距离：", self._nbt_export_persp_min)

        self._nbt_export_persp_diag = QDoubleSpinBox()
        self._nbt_export_persp_diag.setRange(0.0, 2.0)
        self._nbt_export_persp_diag.setDecimals(3)
        self._nbt_export_persp_diag.setSingleStep(0.01)
        self._nbt_export_persp_diag.setToolTip(
            f"在按视锥算出的距离上，再按结构对角线长度加上的额外距离。默认值：{NBT_EXPORT_FULL_PERSPECTIVE_DIAG_EXTRA_DEFAULT}。"
        )
        form_exp.addRow("透视 · 对角线附加距离：", self._nbt_export_persp_diag)

        self._nbt_export_ortho_pad = QDoubleSpinBox()
        self._nbt_export_ortho_pad.setRange(0.0, 50.0)
        self._nbt_export_ortho_pad.setDecimals(3)
        self._nbt_export_ortho_pad.setSingleStep(0.1)
        self._nbt_export_ortho_pad.setToolTip(
            f"正交模式下，在等效半径 r 上再增加的半高需求（方块单位）。默认值：{NBT_EXPORT_FULL_ORTHOGRAPHIC_NEED_HALF_PADDING_DEFAULT}。"
        )
        form_exp.addRow("正交 · 半高需求加量：", self._nbt_export_ortho_pad)

        self._nbt_export_ortho_scale = QDoubleSpinBox()
        self._nbt_export_ortho_scale.setRange(0.05, 2.0)
        self._nbt_export_ortho_scale.setDecimals(3)
        self._nbt_export_ortho_scale.setSingleStep(0.01)
        self._nbt_export_ortho_scale.setToolTip(
            f"用于由半高需求换算相机距离，并作为正交投影半高 = 距离×本系数 的比例。默认值：{NBT_EXPORT_FULL_ORTHOGRAPHIC_HEIGHT_SCALE_DEFAULT}。"
        )
        form_exp.addRow("正交 · 高度换算比例：", self._nbt_export_ortho_scale)

        self._nbt_export_ortho_diag = QDoubleSpinBox()
        self._nbt_export_ortho_diag.setRange(0.0, 2.0)
        self._nbt_export_ortho_diag.setDecimals(3)
        self._nbt_export_ortho_diag.setSingleStep(0.01)
        self._nbt_export_ortho_diag.setToolTip(
            f"正交距离公式中按结构对角线长度加上的额外项。默认值：{NBT_EXPORT_FULL_ORTHOGRAPHIC_DIAG_EXTRA_DEFAULT}。"
        )
        form_exp.addRow("正交 · 对角线附加距离：", self._nbt_export_ortho_diag)

        self._nbt_export_ortho_min = QDoubleSpinBox()
        self._nbt_export_ortho_min.setRange(0.5, 500.0)
        self._nbt_export_ortho_min.setDecimals(3)
        self._nbt_export_ortho_min.setSingleStep(0.5)
        self._nbt_export_ortho_min.setToolTip(
            f"正交模式下相机距离下限。默认值：{NBT_EXPORT_FULL_ORTHOGRAPHIC_MIN_DISTANCE_DEFAULT}。"
        )
        form_exp.addRow("正交 · 最小距离：", self._nbt_export_ortho_min)

        self._nbt_export_ortho_hmin = QDoubleSpinBox()
        self._nbt_export_ortho_hmin.setRange(0.1, 100.0)
        self._nbt_export_ortho_hmin.setDecimals(3)
        self._nbt_export_ortho_hmin.setSingleStep(0.1)
        self._nbt_export_ortho_hmin.setToolTip(
            f"正交投影半高的下限（方块单位），避免过小导致裁切。默认值：{NBT_EXPORT_FULL_ORTHOGRAPHIC_HALF_HEIGHT_MIN_DEFAULT}。"
        )
        form_exp.addRow("正交 · 投影半高下限：", self._nbt_export_ortho_hmin)

        body_lay.addWidget(g_theme)
        body_lay.addWidget(g_dev)
        body_lay.addWidget(g_perf)
        body_lay.addWidget(g_render)
        body_lay.addWidget(g_nbt)
        body_lay.addWidget(g_nbt_export)
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
        self._nbt_viewer_camera_debug.toggled.connect(self._persist)
        self._nbt_large_structure_threshold.valueChanged.connect(self._persist)
        self._nbt_export_margin.valueChanged.connect(self._persist)
        self._nbt_export_persp_min.valueChanged.connect(self._persist)
        self._nbt_export_persp_diag.valueChanged.connect(self._persist)
        self._nbt_export_ortho_pad.valueChanged.connect(self._persist)
        self._nbt_export_ortho_scale.valueChanged.connect(self._persist)
        self._nbt_export_ortho_diag.valueChanged.connect(self._persist)
        self._nbt_export_ortho_min.valueChanged.connect(self._persist)
        self._nbt_export_ortho_hmin.valueChanged.connect(self._persist)
        self._block_icon_preload.currentIndexChanged.connect(self._on_block_icon_preload_changed)
        self._material_list_prewarm.currentIndexChanged.connect(self._persist)

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
        self._nbt_viewer_camera_debug.setChecked(s.nbt_viewer_camera_debug)
        self._nbt_large_structure_threshold.setValue(s.nbt_viewer_large_structure_threshold)
        self._nbt_mcmeta_last_choice = s.nbt_mcmeta_target_version
        self._nbt_export_margin.setValue(s.nbt_export_full_margin)
        self._nbt_export_persp_min.setValue(s.nbt_export_full_perspective_min_distance)
        self._nbt_export_persp_diag.setValue(s.nbt_export_full_perspective_diag_extra)
        self._nbt_export_ortho_pad.setValue(s.nbt_export_full_orthographic_need_half_padding)
        self._nbt_export_ortho_scale.setValue(s.nbt_export_full_orthographic_height_scale)
        self._nbt_export_ortho_diag.setValue(s.nbt_export_full_orthographic_diag_extra)
        self._nbt_export_ortho_min.setValue(s.nbt_export_full_orthographic_min_distance)
        self._nbt_export_ortho_hmin.setValue(s.nbt_export_full_orthographic_half_height_min)
        bidx = self._block_icon_preload.findData(s.block_icon_preload_mode)
        self._block_icon_preload.setCurrentIndex(bidx if bidx >= 0 else 0)
        midx = self._material_list_prewarm.findData(s.material_list_prewarm_mode)
        self._material_list_prewarm.setCurrentIndex(midx if midx >= 0 else 0)
        self._committed_block_icon_mode = self._block_icon_preload.currentData()
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
            nbt_viewer_camera_debug=self._nbt_viewer_camera_debug.isChecked(),
            nbt_viewer_large_structure_threshold=self._nbt_large_structure_threshold.value(),
            nbt_mcmeta_target_version=self._nbt_mcmeta_last_choice.strip(),
            nbt_export_full_margin=self._nbt_export_margin.value(),
            nbt_export_full_perspective_min_distance=self._nbt_export_persp_min.value(),
            nbt_export_full_perspective_diag_extra=self._nbt_export_persp_diag.value(),
            nbt_export_full_orthographic_need_half_padding=self._nbt_export_ortho_pad.value(),
            nbt_export_full_orthographic_height_scale=self._nbt_export_ortho_scale.value(),
            nbt_export_full_orthographic_diag_extra=self._nbt_export_ortho_diag.value(),
            nbt_export_full_orthographic_min_distance=self._nbt_export_ortho_min.value(),
            nbt_export_full_orthographic_half_height_min=self._nbt_export_ortho_hmin.value(),
            block_icon_preload_mode=self._block_icon_preload.currentData(),
            material_list_prewarm_mode=self._material_list_prewarm.currentData(),
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
            "请打开「管理游戏资源」下载资源，并点击对应行的「应用」。"
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

    def _on_lang_manage_clicked(self) -> None:
        dlg = GameResourceLanguageDialog(self)
        dlg.exec()

    def _on_block_icon_manage_clicked(self) -> None:
        dlg = GameResourceBlockIconDialog(self)
        dlg.exec()

    def _on_block_icon_preload_changed(self, index: int) -> None:
        if self._loading:
            return
        new_mode = self._block_icon_preload.itemData(index)
        old_committed = self._committed_block_icon_mode
        if (
            new_mode == BLOCK_ICON_PRELOAD_STARTUP
            and old_committed != BLOCK_ICON_PRELOAD_STARTUP
            and not material_list_icon_prewarm_cache_has_entries()
        ):
            r = QMessageBox.question(
                self,
                "方块图标预加载",
                "现在将立即加载图标，可能会影响性能，你确定要继续吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if r != QMessageBox.StandardButton.Yes:
                self._loading = True
                revert = self._block_icon_preload.findData(old_committed)
                self._block_icon_preload.setCurrentIndex(revert if revert >= 0 else 0)
                self._loading = False
                return
        self._committed_block_icon_mode = new_mode
        self._persist()

    def _persist(self) -> None:
        if self._loading:
            return
        s = self.current_settings()
        save_settings(s)
        self.settings_changed.emit(s)
