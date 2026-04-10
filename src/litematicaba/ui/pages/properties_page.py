"""属性页（design §2.3）：投影头部元数据 SNBT 读写。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from litematicaba.core.snbt_properties import SnbtProperties, load_snbt_properties, save_snbt_properties


class _PreviewCanvas(QFrame):
    """预览图画布：固定 140x140，可缩放显示导入结果。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("propertiesPreviewCanvas")
        self.setFrameShape(QFrame.Shape.Box)
        self.setFixedSize(140, 140)
        self._pixmap: QPixmap | None = None

    def set_preview(self, pixmap: QPixmap | None) -> None:
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(20, 20, 20, 18))
        if self._pixmap is None or self._pixmap.isNull():
            painter.setPen(self.palette().mid().color())
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "140 x 140")
            return
        fitted = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - fitted.width()) // 2
        y = (self.height() - fitted.height()) // 2
        painter.drawPixmap(x, y, fitted)


class PropertiesPage(QWidget):
    """属性页：加载、编辑并保存 Metadata 属性。"""

    def __init__(self) -> None:
        super().__init__()
        self._loading = True
        self._dirty = False
        self._current_data = SnbtProperties()
        self._preview_image = QImage()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(scroll)

        body = QWidget()
        scroll.setWidget(body)
        body_l = QVBoxLayout(body)
        body_l.setContentsMargins(16, 16, 16, 16)
        body_l.setSpacing(12)

        body_l.addLayout(self._build_file_select_row())
        body_l.addWidget(self._build_basic_meta_box())
        body_l.addLayout(self._build_meta_and_preview_row())
        body_l.addWidget(self._build_version_box())
        body_l.addWidget(self._build_regions_box())
        body_l.addStretch()
        body_l.addLayout(self._build_footer_row())

        self._wire_change_tracking()
        self._apply_model_to_ui(self._current_data)
        self._loading = False

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
        box = QGroupBox("文件")
        form = QFormLayout(box)
        self._file_name_edit = QLineEdit()
        self._file_name_edit.setPlaceholderText("文件名称")
        form.addRow("文件名称：", self._file_name_edit)
        return box

    def _build_meta_and_preview_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(self._build_snbt_box(), 2)
        row.addWidget(self._build_preview_box(), 1)
        return row

    def _build_snbt_box(self) -> QGroupBox:
        box = QGroupBox("SNBT 元数据")
        form = QFormLayout(box)

        self._author_edit = QLineEdit()
        self._description_edit = QLineEdit()
        self._created_time_readonly = QLineEdit()
        self._modified_time_readonly = QLineEdit()
        self._size_x_readonly = QLineEdit()
        self._size_y_readonly = QLineEdit()
        self._size_z_readonly = QLineEdit()
        self._total_blocks_readonly = QLineEdit()
        self._total_volume_readonly = QLineEdit()

        self._created_time_readonly.setReadOnly(True)
        self._modified_time_readonly.setReadOnly(True)
        self._size_x_readonly.setReadOnly(True)
        self._size_y_readonly.setReadOnly(True)
        self._size_z_readonly.setReadOnly(True)
        self._total_blocks_readonly.setReadOnly(True)
        self._total_volume_readonly.setReadOnly(True)
        for w in (
            self._size_x_readonly,
            self._size_y_readonly,
            self._size_z_readonly,
            self._total_blocks_readonly,
            self._total_volume_readonly,
        ):
            w.setMaximumWidth(120)

        form.addRow("作者（Author）：", self._author_edit)
        form.addRow("描述（Description）：", self._description_edit)
        form.addRow("创建时间：", self._created_time_readonly)
        form.addRow("修改时间：", self._modified_time_readonly)
        form.addRow("尺寸：", self._build_size_row_widget())
        form.addRow("体积：", self._build_volume_row_widget())
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
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(QLabel("方块:"))
        row.addWidget(self._total_blocks_readonly)
        row.addWidget(QLabel("总计:"))
        row.addWidget(self._total_volume_readonly)
        row.addStretch()
        return w

    def _build_preview_box(self) -> QGroupBox:
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
        box = QGroupBox("版本信息")
        form = QFormLayout(box)
        self._litematica_ver_readonly = QLineEdit()
        self._mc_data_ver_readonly = QLineEdit()
        self._litematica_ver_readonly.setReadOnly(True)
        self._mc_data_ver_readonly.setReadOnly(True)
        form.addRow("投影文件版本：", self._litematica_ver_readonly)
        form.addRow("Minecraft 数据版本：", self._mc_data_ver_readonly)
        return box

    def _build_regions_box(self) -> QGroupBox:
        box = QGroupBox("区域列表（后续设计）")
        lay = QVBoxLayout(box)
        self._regions_list = QListWidget()
        self._regions_list.addItem("（暂无区域，后续接入真实数据）")
        self._regions_list.setEnabled(False)
        lay.addWidget(self._regions_list)
        return box

    def _build_footer_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
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
        self._file_name_edit.textChanged.connect(self._mark_dirty)
        self._author_edit.textChanged.connect(self._mark_dirty)
        self._description_edit.textChanged.connect(self._mark_dirty)

    def _on_choose_external_file(self) -> None:
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
        self._show_not_implemented("在库中选择")

    def _on_clear_preview(self) -> None:
        self._preview_image = QImage()
        self._preview_canvas.set_preview(None)
        self._preview_count_hint.setText("PreviewImageData: 0 项")
        self._mark_dirty()

    def _on_import_preview(self) -> None:
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
        self._preview_count_hint.setText(f"PreviewImageData: {140 * 140} 项")
        self._mark_dirty()

    def _on_restore_defaults(self) -> None:
        if self._current_data.file_path is None:
            QMessageBox.information(self, "恢复默认值", "请先加载一个投影文件。")
            return
        self._author_edit.clear()
        self._description_edit.clear()
        self._created_time_readonly.setText(self._format_timestamp(0))
        self._modified_time_readonly.setText(self._format_timestamp(0))
        self._on_clear_preview()
        self._mark_dirty()

    def _on_save(self) -> None:
        if self._current_data.file_path is None:
            QMessageBox.information(self, "保存", "请先选择一个 .litematic 文件。")
            return
        try:
            model = self._collect_ui_to_model()
            save_snbt_properties(model)
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", f"写入 SNBT 失败：\n{exc}")
            return
        self._current_data = model
        self._dirty = False
        self._sync_title_hint()
        QMessageBox.information(self, "保存", "已保存到原文件。")

    def _on_save_as(self) -> None:
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
        try:
            data = load_snbt_properties(file_path)
        except Exception as exc:
            QMessageBox.critical(self, "打开失败", f"读取 SNBT 失败：\n{exc}")
            return
        self._current_data = data
        self._loading = True
        self._apply_model_to_ui(data)
        self._loading = False
        self._dirty = False
        self._sync_title_hint()

    def _apply_model_to_ui(self, data: SnbtProperties) -> None:
        self._active_file_hint.setText(str(data.file_path) if data.file_path else "当前未激活文件")
        self._file_name_edit.setText(data.file_name)
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
        self._litematica_ver_readonly.setText(str(data.litematic_version))
        self._mc_data_ver_readonly.setText(str(data.minecraft_data_version))
        self._set_preview_from_argb_list(data.preview_image_data)

    def _collect_ui_to_model(self) -> SnbtProperties:
        model = SnbtProperties(
            file_path=self._current_data.file_path,
            file_name=self._file_name_edit.text().strip(),
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
        )
        return model

    def _set_preview_from_argb_list(self, data: list[int]) -> None:
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
                image.setPixel(x, y, int(data[base + x]) & 0xFFFFFFFF)
        self._preview_image = image
        self._preview_canvas.set_preview(QPixmap.fromImage(self._preview_image))
        self._preview_count_hint.setText(f"PreviewImageData: {len(data)} 项")

    def _preview_to_argb_list(self) -> list[int]:
        if self._preview_image.isNull():
            return []
        image = self._preview_image.convertToFormat(QImage.Format.Format_ARGB32)
        out: list[int] = []
        for y in range(image.height()):
            for x in range(image.width()):
                out.append(int(image.pixel(x, y)))
        return out

    def _on_clear_preview_no_dirty(self) -> None:
        self._preview_image = QImage()
        self._preview_canvas.set_preview(None)
        self._preview_count_hint.setText("PreviewImageData: 0 项")

    def _confirm_discard_if_dirty(self) -> bool:
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
        if self._loading:
            return
        self._dirty = True
        self._sync_title_hint()

    def _sync_title_hint(self) -> None:
        base = str(self._current_data.file_path) if self._current_data.file_path else "当前未激活文件"
        self._active_file_hint.setText(f"{base}{' *' if self._dirty else ''}")

    @staticmethod
    def _format_timestamp(ts: int) -> str:
        if ts <= 0:
            return "-"
        try:
            sec = ts / 1000 if ts > 10_000_000_000 else ts
            dt = datetime.fromtimestamp(sec)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(ts)

    def _show_not_implemented(self, action: str) -> None:
        QMessageBox.information(self, "属性页", f"{action} 功能将在后续接入真实读写逻辑。")
