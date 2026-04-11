"""属性页（设计文档 §2.3）：Litematica 投影头部元数据的展示与编辑。

本模块实现「属性」标签页 UI，负责：
- 从 .litematic 文件加载 SNBT 中的 Metadata 相关字段（通过 ``SnbtProperties``）；
- 在表单中编辑可写字段（展示用 ``file_name``、Metadata ``Name``/作者/描述、预览图等），只读字段展示尺寸、版本、时间戳、**密度**等；
- 将修改写回原文件或「另存为」新路径。
- 根级 ``Regions``：表格展示各子区域名称（可编辑）、``Size``/``Position`` 的 x/y/z（只读）；保存时按行顺序重写 ``Regions`` 键名。

**布局：** 中间 ``QScrollArea`` 承载表单（stretch=1），底部 ``footer_bar`` 单独一行承载保存等按钮，按钮条不随内容滚动。

**密度（体积行）：** 非 SNBT 持久化字段，由 ``TotalBlocks / TotalVolume`` 派生，格式为一位小数的百分数，表示非空气方块占包围体素格数的比例；``TotalVolume<=0`` 时显示 ``-``。

**内部名称：** 对应 Metadata 的 ``Name`` 字符串，与「文件」分组中的显示用 ``file_name``（默认与磁盘文件名一致）语义不同。

状态约定：
- ``_loading``：为 True 时忽略 ``textChanged`` 触发的脏标记，避免程序化填充 UI 时误标为已修改；
- ``_dirty``：用户是否改动了相对磁盘上的当前内容；换文件前会据此弹出是否丢弃的确认框。
- ``_baseline_snapshot``：最近一次成功从磁盘加载后的元数据快照；「恢复默认值」将当前编辑还原为该快照（非清空表单）；**保存到原文件不会刷新快照**。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap, QResizeEvent, QShowEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QAbstractItemView,
    QMessageBox,
    QPushButton,
    QHeaderView,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from litematicaba.core.snbt_properties import (
    RegionInfo,
    SnbtProperties,
    copy_snbt_properties,
    load_snbt_properties,
    regions_after_save_commit,
    save_snbt_properties,
)
from litematicaba.ui.theme import current_theme_id
from litematicaba.ui.widgets.themed_plain_table import ThemedPlainQTableWidget


class _PreviewCanvas(QFrame):
    """固定 140×140 的预览区域，将任意比例的 ``QPixmap`` 居中、等比缩放后绘制。

    无图时显示占位文案与半透明底，便于与正式预览区分。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("propertiesPreviewCanvas")
        self.setFrameShape(QFrame.Shape.Box)
        self.setFixedSize(140, 140)
        self._pixmap: QPixmap | None = None  # 当前要绘制的位图；None 表示占位状态

    def set_preview(self, pixmap: QPixmap | None) -> None:
        """更新预览内容并触发重绘。"""
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)
        painter = QPainter(self)
        # 轻微暗底，使浅色预览边缘在浅色主题下仍可见
        painter.fillRect(self.rect(), QColor(20, 20, 20, 18))
        if self._pixmap is None or self._pixmap.isNull():
            painter.setPen(self.palette().mid().color())
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "140 x 140")
            return
        # KeepAspectRatio：在 140×140 内完整显示，可能留边
        fitted = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - fitted.width()) // 2
        y = (self.height() - fitted.height()) // 2
        painter.drawPixmap(x, y, fitted)


class PropertiesPage(QWidget):
    """主属性页：中间内容为可滚动区域，底部操作按钮条固定在页面下沿（不参与滚动）。"""

    @staticmethod
    def _align_numeric_line_edit(w: QLineEdit) -> None:
        """尺寸、体积、版本号等纯数字只读框：文本右对齐便于纵列对比位数。"""
        w.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def __init__(self) -> None:
        super().__init__()
        # 初次构建 UI 期间为 True，避免 setText 等触发 _mark_dirty
        self._loading = True
        self._dirty = False
        self._current_data = SnbtProperties()
        # 内存中的预览图（ARGB）；与文件里 PreviewImageData 列表互转
        self._preview_image = QImage()
        # 完整路径提示（含未保存星号）；显示用中间省略，完整内容在 ToolTip
        self._full_file_hint_text = ""
        # 成功 load 后的元数据副本，供「恢复默认值」撤销自打开以来的编辑（保存后亦不自动刷新此快照）
        self._baseline_snapshot: SnbtProperties | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # stretch=1：滚动区占满标题栏与页脚之间的剩余高度；页脚始终在可视区域底边
        root.addWidget(scroll, 1)

        body = QWidget()
        body.setMinimumWidth(0)
        scroll.setWidget(body)
        body_l = QVBoxLayout(body)
        body_l.setContentsMargins(16, 16, 16, 16)
        body_l.setSpacing(12)

        body_l.addLayout(self._build_file_select_row())
        body_l.addWidget(self._build_basic_meta_box())
        body_l.addLayout(self._build_meta_and_preview_row())
        body_l.addWidget(self._build_version_box())
        body_l.addWidget(self._build_regions_box())

        # 与 body 左右边距对齐；上 8px 与滚动内容留出缝隙，下 16px 贴窗口底
        footer_bar = QWidget()
        footer_lay = QVBoxLayout(footer_bar)
        footer_lay.setContentsMargins(16, 8, 16, 16)
        footer_lay.setSpacing(0)
        footer_lay.addLayout(self._build_footer_row())
        root.addWidget(footer_bar)

        self._wire_change_tracking()
        self._apply_model_to_ui(self._current_data)
        self._loading = False
        # 允许 QLineEdit 在窄布局下收缩，避免把整行撑得过宽
        self._apply_line_edit_horizontal_shrink()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        # 路径标签宽度随窗口变化，需重新计算中间省略
        self._update_file_hint_elide()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        # Minecraft 主题下列较窄时 SNBT 表单易挤成一团，给左列设最小宽度
        self._apply_snbt_column_min_width()
        self.apply_regions_table_theme()
        # 首帧布局完成后宽度才稳定，延迟一次省略计算
        QTimer.singleShot(0, self._update_file_hint_elide)

    def apply_regions_table_theme(self) -> None:
        """与 UI 测试页内容列表一致，随全局主题刷新区域表样式与行高。"""
        app = QApplication.instance()
        if app is None:
            return
        self._regions_table.apply_theme(current_theme_id(app))
        self._regions_table.sync_row_heights()

    # -------------------------------------------------------------------------
    # UI 构建：自上而下与主窗口 body 结构一致
    # -------------------------------------------------------------------------

    def _build_file_select_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self._btn_choose_external = QPushButton("选择文件...")
        self._btn_choose_library = QPushButton("在库中选择...")
        self._active_file_hint = QLabel("当前未激活文件")
        self._active_file_hint.setStyleSheet("color: palette(mid);")
        self._active_file_hint.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(self._btn_choose_external)
        row.addWidget(self._btn_choose_library)
        row.addWidget(self._active_file_hint, 1)

        self._btn_choose_external.clicked.connect(self._on_choose_external_file)
        self._btn_choose_library.clicked.connect(self._on_choose_from_library)
        return row

    def _build_basic_meta_box(self) -> QGroupBox:
        """「文件名称」：UI 展示用名，当前实现中与加载路径的 ``path.name`` 同步，**不是** Metadata ``Name``。

        真正的内部标识见 SNBT 分组中的「内部名称」（``internal_name`` ↔ ``Metadata.Name``）。
        """
        box = QGroupBox("文件")
        form = QFormLayout(box)
        self._file_name_edit = QLineEdit()
        self._file_name_edit.setPlaceholderText("文件名称")
        form.addRow("文件名称：", self._file_name_edit)
        return box

    def _build_meta_and_preview_row(self) -> QHBoxLayout:
        """左侧 SNBT 表单（stretch 2）+ 右侧预览（stretch 1），横向并排。"""
        row = QHBoxLayout()
        row.setSpacing(12)
        self._snbt_column = QWidget()
        self._snbt_column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._snbt_column.setMinimumWidth(0)
        snbt_outer = QVBoxLayout(self._snbt_column)
        snbt_outer.setContentsMargins(0, 0, 0, 0)
        snbt_outer.addWidget(self._build_snbt_box())
        preview_box = self._build_preview_box()
        preview_box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        row.addWidget(self._snbt_column, 2)
        row.addWidget(preview_box, 1)
        return row

    def _build_snbt_box(self) -> QGroupBox:
        """Metadata 主表单。

        写回 ``save_snbt_properties`` 的字符串字段由本分组的可编辑行提供：``Name``/``Author``/``Description``（及预览像素数组，见预览区）。
        「文件」分组里的 ``file_name`` 属独立控件，**无对应 Metadata 键**，另存为默认名等使用 ``SnbtProperties.file_name``。
        只读：时间、包围尺寸、``TotalBlocks``/``TotalVolume``、**密度**（两统计量比值，不落盘）。
        """
        box = QGroupBox("SNBT 元数据")
        form = QFormLayout(box)

        # Litematica Metadata.Name：游戏/材料列表等使用的内部名，可与磁盘文件名不同
        self._internal_name_edit = QLineEdit()
        self._author_edit = QLineEdit()
        self._description_edit = QLineEdit()
        self._created_time_readonly = QLineEdit()
        self._modified_time_readonly = QLineEdit()
        self._size_x_readonly = QLineEdit()
        self._size_y_readonly = QLineEdit()
        self._size_z_readonly = QLineEdit()
        self._total_blocks_readonly = QLineEdit()
        self._total_volume_readonly = QLineEdit()
        # 占用率 = TotalBlocks/TotalVolume，仅展示；保存时不写入 NBT（无对应键）
        self._density_readonly = QLineEdit()

        # 时间、包围盒尺寸、方块/总计/密度等由文件解析结果派生，用户不可在此直接改 SNBT 统计字段
        self._created_time_readonly.setReadOnly(True)
        self._modified_time_readonly.setReadOnly(True)
        self._size_x_readonly.setReadOnly(True)
        self._size_y_readonly.setReadOnly(True)
        self._size_z_readonly.setReadOnly(True)
        self._total_blocks_readonly.setReadOnly(True)
        self._total_volume_readonly.setReadOnly(True)
        self._density_readonly.setReadOnly(True)
        for w in (
            self._size_x_readonly,
            self._size_y_readonly,
            self._size_z_readonly,
            self._total_blocks_readonly,
            self._total_volume_readonly,
            self._density_readonly,
        ):
            w.setMaximumWidth(120)
            self._align_numeric_line_edit(w)

        form.addRow("内部名称：", self._internal_name_edit)
        form.addRow("作者：", self._author_edit)
        form.addRow("描述：", self._description_edit)
        form.addRow("创建时间：", self._created_time_readonly)
        form.addRow("修改时间：", self._modified_time_readonly)
        form.addRow("尺寸：", self._build_size_row_widget())
        form.addRow("体积：", self._build_volume_row_widget())
        form.setHorizontalSpacing(8)
        return box

    def _build_size_row_widget(self) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(QLabel("x:"))
        row.addWidget(self._size_x_readonly)
        row.addWidget(QLabel("y:"))
        row.addWidget(self._size_y_readonly)
        row.addWidget(QLabel("z:"))
        row.addWidget(self._size_z_readonly)
        row.addStretch()
        return w

    def _build_volume_row_widget(self) -> QWidget:
        """单行展示 ``TotalBlocks``、``TotalVolume`` 及由二者计算的密度百分数。"""
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(QLabel("方块:"))
        row.addWidget(self._total_blocks_readonly)
        row.addWidget(QLabel("总计:"))
        row.addWidget(self._total_volume_readonly)
        row.addWidget(QLabel("密度:"))
        row.addWidget(self._density_readonly)
        row.addStretch()
        return w

    def _build_preview_box(self) -> QGroupBox:
        """PreviewImageData：导入外部图或从文件加载；缩放算法影响写入 140×140 时的采样方式。"""
        box = QGroupBox("预览图")
        lay = QVBoxLayout(box)
        lay.setSpacing(8)

        self._preview_canvas = _PreviewCanvas()
        self._preview_count_hint = QLabel("PreviewImageData: 0 项")
        self._preview_count_hint.setStyleSheet("color: palette(mid);")
        self._preview_sample_combo = QComboBox()
        self._preview_sample_combo.addItem("平滑（Smooth）", Qt.TransformationMode.SmoothTransformation)
        self._preview_sample_combo.addItem("邻近（Nearest）", Qt.TransformationMode.FastTransformation)
        self._btn_clear_preview = QPushButton("清空预览图")
        self._btn_import_preview = QPushButton("导入预览图")

        lay.addWidget(self._preview_canvas, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(self._preview_count_hint)
        lay.addWidget(QLabel("缩放采样方式："))
        lay.addWidget(self._preview_sample_combo)
        lay.addWidget(self._btn_clear_preview)
        lay.addWidget(self._btn_import_preview)
        lay.addStretch()

        self._btn_clear_preview.clicked.connect(self._on_clear_preview)
        self._btn_import_preview.clicked.connect(self._on_import_preview)
        return box

    def _build_version_box(self) -> QGroupBox:
        """Litematica 文件格式版本与 Minecraft 数据版本，仅展示。"""
        box = QGroupBox("版本信息")
        form = QFormLayout(box)
        self._litematica_ver_readonly = QLineEdit()
        self._mc_data_ver_readonly = QLineEdit()
        self._litematica_ver_readonly.setReadOnly(True)
        self._mc_data_ver_readonly.setReadOnly(True)
        self._align_numeric_line_edit(self._litematica_ver_readonly)
        self._align_numeric_line_edit(self._mc_data_ver_readonly)
        form.addRow("投影文件版本：", self._litematica_ver_readonly)
        form.addRow("Minecraft 数据版本：", self._mc_data_ver_readonly)
        form.setHorizontalSpacing(8)
        return box

    def _build_regions_box(self) -> QGroupBox:
        """根级 ``Regions``：名称可编辑，尺寸与相对位置只读（设计文档 §2.3.4）。"""
        box = QGroupBox("区域列表")
        lay = QVBoxLayout(box)
        app = QApplication.instance()
        _tid = current_theme_id(app) if app is not None else "QTDefault"
        self._regions_table = ThemedPlainQTableWidget(theme_id=_tid)
        self._regions_table.setColumnCount(7)
        self._regions_table.setHorizontalHeaderLabels(
            [
                "区域名称",
                "尺寸 x",
                "尺寸 y",
                "尺寸 z",
                "位置 x",
                "位置 y",
                "位置 z",
            ]
        )
        name_header = self._regions_table.horizontalHeaderItem(0)
        if name_header is not None:
            name_header.setToolTip("双击该列单元格可修改区域名称；也可选中行后按 F2 进入编辑。")
        self._regions_table.verticalHeader().setVisible(False)
        self._regions_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._regions_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        rh = self._regions_table.horizontalHeader()
        rh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, 7):
            rh.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self._regions_table.setMinimumHeight(180)
        self._regions_table.itemChanged.connect(self._on_regions_item_changed)
        lay.addWidget(self._regions_table)
        self._regions_empty_hint = QLabel("当前文件无子区域，或 Regions 无法解析。")
        self._regions_empty_hint.setStyleSheet("color: palette(mid);")
        self._regions_empty_hint.setWordWrap(True)
        lay.addWidget(self._regions_empty_hint)
        return box

    def _build_footer_row(self) -> QHBoxLayout:
        """保存 / 另存为 / 恢复为打开文件时的快照；转换格式尚未实现。

        由 ``__init__`` 放入 ``PropertiesPage`` 根布局底部，置于 ``QScrollArea`` 之外，故不随表单滚动。

        相邻按钮间距 = 当前样式 ``PM_LayoutHorizontalSpacing`` + 8px（该指标为 -1 时按 6px 计），避免 Metro10 / Minecraft 等大按钮主题下控件挤在一起。
        """
        row = QHBoxLayout()
        # 在主题默认水平间距上 +8px，避免高按钮样式（Metro10、Minecraft）下相邻按钮视觉粘连
        style = self.style()
        base = 6
        if style is not None:
            pm = style.pixelMetric(QStyle.PixelMetric.PM_LayoutHorizontalSpacing)
            if pm >= 0:
                base = pm
        row.setSpacing(base + 8)
        row.addStretch()
        self._btn_save = QPushButton("保存")
        self._btn_save_as = QPushButton("另存为")
        self._btn_restore = QPushButton("恢复默认值")
        self._btn_convert = QPushButton("转换格式")
        self._btn_convert.setEnabled(False)

        self._btn_save.clicked.connect(self._on_save)
        self._btn_save_as.clicked.connect(self._on_save_as)
        self._btn_restore.clicked.connect(self._on_restore_defaults)
        self._btn_convert.clicked.connect(lambda: self._show_not_implemented("转换格式"))

        row.addWidget(self._btn_save)
        row.addWidget(self._btn_save_as)
        row.addWidget(self._btn_restore)
        row.addWidget(self._btn_convert)
        return row

    def _wire_change_tracking(self) -> None:
        """仅对会写回 SNBT 的输入框挂接脏标记；只读控件不连接。"""
        self._file_name_edit.textChanged.connect(self._mark_dirty)
        self._internal_name_edit.textChanged.connect(self._mark_dirty)
        self._author_edit.textChanged.connect(self._mark_dirty)
        self._description_edit.textChanged.connect(self._mark_dirty)

    def _on_regions_item_changed(self, item: QTableWidgetItem) -> None:
        """仅「区域名称」列（第 0 列）的编辑触发脏标记。"""
        if item.column() != 0:
            return
        self._mark_dirty()

    def _apply_regions_table(self, data: SnbtProperties) -> None:
        """用模型填充区域表；在 ``_loading`` 为 True 时调用可避免触发 ``itemChanged`` 脏标记。"""
        self._regions_table.blockSignals(True)
        self._regions_table.setRowCount(0)
        ro = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        editable = ro | Qt.ItemFlag.ItemIsEditable
        for ri, reg in enumerate(data.regions):
            self._regions_table.insertRow(ri)
            name_item = QTableWidgetItem(reg.name)
            name_item.setFlags(editable)
            self._regions_table.setItem(ri, 0, name_item)
            vals = (*reg.size, *reg.position)
            for ci, val in enumerate(vals, start=1):
                cell = QTableWidgetItem(str(val))
                cell.setFlags(ro)
                self._regions_table.setItem(ri, ci, cell)
        self._regions_table.blockSignals(False)
        self._regions_empty_hint.setVisible(len(data.regions) == 0)
        self._regions_table.sync_row_heights()

    def _collect_regions_from_table(self) -> list[RegionInfo]:
        """行序与 ``_current_data.regions`` 对齐；只从第 0 列读取新名称，几何字段沿用模型。"""
        rows = self._regions_table.rowCount()
        base = self._current_data.regions
        if rows == 0:
            return []
        out: list[RegionInfo] = []
        for i in range(rows):
            name_item = self._regions_table.item(i, 0)
            name = name_item.text().strip() if name_item is not None else ""
            if i < len(base):
                b = base[i]
                out.append(RegionInfo(source_key=b.source_key, name=name, size=b.size, position=b.position))
            else:
                out.append(RegionInfo(source_key=name, name=name, size=(0, 0, 0), position=(0, 0, 0)))
        return out

    # -------------------------------------------------------------------------
    # 槽函数：文件选择、预览、保存
    # -------------------------------------------------------------------------

    def _on_choose_external_file(self) -> None:
        """通过系统对话框打开 .litematic；若有未保存修改先确认是否丢弃。"""
        if not self._confirm_discard_if_dirty():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择投影文件",
            "",
            "Litematic Files (*.litematic);;All Files (*.*)",
        )
        if not path:
            return
        self._load_from_file(path)

    def _on_choose_from_library(self) -> None:
        """项目内「库」选择器尚未接入。"""
        self._show_not_implemented("在库中选择")

    def _on_clear_preview(self) -> None:
        """清空内存预览与画布，并标记脏（将写入空的 PreviewImageData）。"""
        self._preview_image = QImage()
        self._preview_canvas.set_preview(None)
        self._preview_count_hint.setText("PreviewImageData: 0 项")
        self._mark_dirty()

    def _on_import_preview(self) -> None:
        """居中裁成正方形后缩放到 140×140，与 Litematica 常见预览尺寸一致。"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "导入预览图",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*.*)",
        )
        if not path:
            return

        raw = QImage(path)
        if raw.isNull():
            QMessageBox.warning(self, "导入预览图", "图片读取失败，请更换文件后重试。")
            return

        # 取最短边为边长，从中心裁剪，避免非正方形原图被强行拉伸变形
        side = min(raw.width(), raw.height())
        crop_x = (raw.width() - side) // 2
        crop_y = (raw.height() - side) // 2
        square = raw.copy(crop_x, crop_y, side, side)
        mode = self._preview_sample_combo.currentData()
        if mode is None:
            mode = Qt.TransformationMode.SmoothTransformation
        self._preview_image = square.scaled(
            140,
            140,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            mode,
        )
        pix = QPixmap.fromImage(self._preview_image)
        self._preview_canvas.set_preview(pix)
        # 固定 140×140 像素 → ARGB 列表长度恒为 19600
        self._preview_count_hint.setText(f"PreviewImageData: {140 * 140} 项")
        self._mark_dirty()

    def _on_restore_defaults(self) -> None:
        """用 ``_baseline_snapshot`` 覆盖 ``_current_data`` 并刷新 UI。

        先置 ``_dirty=False`` 再 ``_apply_model_to_ui``，避免路径标签仍带未保存星号。
        快照仅在 ``_load_from_file`` 成功时更新；保存、编辑不会改写快照。
        """
        if self._current_data.file_path is None:
            QMessageBox.information(self, "恢复默认值", "请先加载一个投影文件。")
            return
        if self._baseline_snapshot is None:
            QMessageBox.information(self, "恢复默认值", "没有可用的加载快照，请重新打开该文件。")
            return
        self._loading = True
        self._dirty = False
        self._current_data = copy_snbt_properties(self._baseline_snapshot)
        self._apply_model_to_ui(self._current_data)
        self._loading = False

    def _on_save(self) -> None:
        """写回 ``_current_data.file_path``；成功后用新模型替换内存状态并清除脏标记。"""
        if self._current_data.file_path is None:
            QMessageBox.information(self, "保存", "请先选择一个 .litematic 文件。")
            return
        try:
            model = self._collect_ui_to_model()
            save_snbt_properties(model)
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", f"写入 SNBT 失败：\n{exc}")
            return
        self._current_data = regions_after_save_commit(model)
        self._dirty = False
        self._sync_title_hint()
        QMessageBox.information(self, "保存", "已保存到原文件。")

    def _on_save_as(self) -> None:
        """写入用户选择的新路径，随后 ``_load_from_file`` 切换到该文件作为当前上下文。"""
        if self._current_data.file_path is None:
            QMessageBox.information(self, "另存为", "请先选择一个 .litematic 文件。")
            return
        default_name = self._file_name_edit.text().strip() or self._current_data.file_path.name
        out, _ = QFileDialog.getSaveFileName(
            self,
            "另存为",
            str(self._current_data.file_path.with_name(default_name)),
            "Litematic Files (*.litematic);;All Files (*.*)",
        )
        if not out:
            return
        try:
            model = self._collect_ui_to_model()
            written = save_snbt_properties(model, out)
        except Exception as exc:
            QMessageBox.critical(self, "另存为失败", f"写入 SNBT 失败：\n{exc}")
            return
        self._load_from_file(written)

    def _load_from_file(self, file_path: str | Path) -> None:
        """解析 SNBT 填充 ``SnbtProperties``，并在 ``_loading`` 保护下刷新全部控件。

        成功后同步更新 ``_baseline_snapshot``，供「恢复默认值」使用。
        """
        try:
            data = load_snbt_properties(file_path)
        except Exception as exc:
            QMessageBox.critical(self, "打开失败", f"读取 SNBT 失败：\n{exc}")
            return
        self._current_data = data
        self._baseline_snapshot = copy_snbt_properties(data)
        self._dirty = False
        self._loading = True
        self._apply_model_to_ui(data)
        self._loading = False

    def _apply_model_to_ui(self, data: SnbtProperties) -> None:
        """单向：数据模型 → 控件文本与预览；不修改 ``_dirty``（由调用方控制）。"""
        self._file_name_edit.setText(data.file_name)
        self._internal_name_edit.setText(data.internal_name)
        self._author_edit.setText(data.author)
        self._description_edit.setText(data.description)
        self._created_time_readonly.setText(self._format_timestamp(data.created_unix))
        self._modified_time_readonly.setText(self._format_timestamp(data.modified_unix))
        ex, ey, ez = data.enclosing_size
        self._size_x_readonly.setText(str(ex))
        self._size_y_readonly.setText(str(ey))
        self._size_z_readonly.setText(str(ez))
        self._total_blocks_readonly.setText(str(data.total_blocks))
        self._total_volume_readonly.setText(str(data.total_volume))
        # 密度随方块数/总计刷新；不参与 _collect_ui_to_model
        self._density_readonly.setText(self._format_block_density_pct(data.total_blocks, data.total_volume))
        self._litematica_ver_readonly.setText(str(data.litematic_version))
        self._mc_data_ver_readonly.setText(str(data.minecraft_data_version))
        self._set_preview_from_argb_list(data.preview_image_data)
        self._apply_regions_table(data)
        self._sync_title_hint()

    def _apply_line_edit_horizontal_shrink(self) -> None:
        """构造完成后统一收紧所有 QLineEdit，利于窄窗口与表单对齐。"""
        for w in self.findChildren(QLineEdit):
            w.setMinimumWidth(0)
            w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _apply_snbt_column_min_width(self) -> None:
        """Minecraft 主题字体/样式下表单更易折行，为 SNBT 列保留最小可读宽度。"""
        app = QApplication.instance()
        tid = current_theme_id(app) if app is not None else "QTDefault"
        if tid == "Minecraft":
            self._snbt_column.setMinimumWidth(400)
        else:
            self._snbt_column.setMinimumWidth(0)

    def _update_file_hint_elide(self) -> None:
        """根据标签可用宽度对路径做中间省略；过窄时用父行宽度估算（减去两侧按钮大致占位）。"""
        text = self._full_file_hint_text
        w = self._active_file_hint.width()
        if w < 48:
            row = self._active_file_hint.parentWidget()
            if row is not None:
                w = max(48, row.width() - 280)
        elided = self._active_file_hint.fontMetrics().elidedText(
            text,
            Qt.TextElideMode.ElideMiddle,
            max(48, w - 8),
        )
        self._active_file_hint.setText(elided)

    def _collect_ui_to_model(self) -> SnbtProperties:
        """从控件组装即将写入磁盘的模型。

        修改时间取当前毫秒；``TotalBlocks``/``TotalVolume``/包围尺寸/版本等沿用 ``_current_data``（用户在本页不能改统计）。
        密度为派生显示，不包含在 ``SnbtProperties`` 中。
        """
        model = SnbtProperties(
            file_path=self._current_data.file_path,
            file_name=self._file_name_edit.text().strip(),
            internal_name=self._internal_name_edit.text().strip(),
            author=self._author_edit.text().strip(),
            description=self._description_edit.text().strip(),
            created_unix=self._current_data.created_unix,
            modified_unix=int(datetime.now().timestamp() * 1000),
            enclosing_size=self._current_data.enclosing_size,
            total_blocks=self._current_data.total_blocks,
            total_volume=self._current_data.total_volume,
            litematic_version=self._current_data.litematic_version,
            minecraft_data_version=self._current_data.minecraft_data_version,
            preview_image_data=self._preview_to_argb_list(),
            regions=self._collect_regions_from_table(),
        )
        return model

    def _set_preview_from_argb_list(self, data: list[int]) -> None:
        """将文件中的 PreviewImageData（每元素 32 位 ARGB）还原为 ``QImage`` 并显示。

        仅当列表长度为完全平方数时才认为合法；否则清空预览且不标脏（加载阶段）。
        """
        if not data:
            self._on_clear_preview_no_dirty()
            return
        side = int(len(data) ** 0.5)
        if side * side != len(data):
            self._on_clear_preview_no_dirty()
            return
        image = QImage(side, side, QImage.Format.Format_ARGB32)
        for y in range(side):
            base = y * side
            for x in range(side):
                # 与 Qt 像素一致，掩掉高位防止有符号扩展问题
                image.setPixel(x, y, int(data[base + x]) & 0xFFFFFFFF)
        self._preview_image = image
        self._preview_canvas.set_preview(QPixmap.fromImage(self._preview_image))
        self._preview_count_hint.setText(f"PreviewImageData: {len(data)} 项")

    def _preview_to_argb_list(self) -> list[int]:
        """将当前 ``_preview_image`` 按行主序展开为与 SNBT 互操作的 int 列表（ARGB32）。"""
        if self._preview_image.isNull():
            return []
        image = self._preview_image.convertToFormat(QImage.Format.Format_ARGB32)
        out: list[int] = []
        for y in range(image.height()):
            for x in range(image.width()):
                out.append(int(image.pixel(x, y)))
        return out

    def _on_clear_preview_no_dirty(self) -> None:
        """与 ``_on_clear_preview`` 相同视觉效果，但不调用 ``_mark_dirty``（用于加载失败或非法数据）。"""
        self._preview_image = QImage()
        self._preview_canvas.set_preview(None)
        self._preview_count_hint.setText("PreviewImageData: 0 项")

    def _confirm_discard_if_dirty(self) -> bool:
        """返回 True 表示可继续（无脏数据或用户确认丢弃）。"""
        if not self._dirty:
            return True
        ans = QMessageBox.question(
            self,
            "未保存更改",
            "当前文件有未保存修改，是否丢弃并继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return ans == QMessageBox.StandardButton.Yes

    def _mark_dirty(self) -> None:
        """由可编辑控件信号触发；加载模型期间由 ``_loading`` 短路。"""
        if self._loading:
            return
        self._dirty = True
        self._sync_title_hint()

    def _sync_title_hint(self) -> None:
        """更新顶部路径文案、ToolTip 与省略显示；未保存时在文案末尾追加 `` *``。"""
        base = str(self._current_data.file_path) if self._current_data.file_path else "当前未激活文件"
        self._full_file_hint_text = f"{base}{' *' if self._dirty else ''}"
        self._active_file_hint.setToolTip(self._full_file_hint_text)
        self._update_file_hint_elide()

    @staticmethod
    def _format_timestamp(ts: int) -> str:
        """将 Unix 时间格式化为本地可读字符串。

        Litematica 常用毫秒（>1e10 阈值），否则按秒处理；无效或异常时退回原始数字或 ``-``。
        """
        if ts <= 0:
            return "-"
        try:
            sec = ts / 1000 if ts > 10_000_000_000 else ts
            dt = datetime.fromtimestamp(sec)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(ts)

    @staticmethod
    def _format_block_density_pct(blocks: int, volume: int) -> str:
        """将 ``TotalBlocks``（非空气方块数）与 ``TotalVolume``（包围体素格数）转为占用率字符串。

        公式 ``100 * blocks / volume``，输出形如 ``12.3%``（固定一位小数）。
        ``volume <= 0`` 时无法定义比例，返回 ``-``（例如未加载或损坏元数据）。
        """
        if volume <= 0:
            return "-"
        pct = 100.0 * float(blocks) / float(volume)
        return f"{pct:.1f}%"

    def _show_not_implemented(self, action: str) -> None:
        """占位功能的统一提示，避免静默无响应。"""
        QMessageBox.information(self, "属性页", f"{action} 功能将在后续接入真实读写逻辑。")
