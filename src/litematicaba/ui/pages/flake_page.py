"""分层页（design §2.6）：legacy 正交 2D 剖面；预览缩放使用邻近采样。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QResizeEvent, QShowEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QComboBox,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from litematicaba.core.litematic_ortho_preview import OrthoViewKind, render_region_ortho_rgba
from litematicaba.ui.material_list_dialog import MaterialListDialog
from litematicaba.ui.pages.properties_page import PropertiesPage

_VIEW_LABELS: list[tuple[OrthoViewKind, str]] = [
    (OrthoViewKind.TOP, "顶视"),
    (OrthoViewKind.NORTH, "北"),
    (OrthoViewKind.SOUTH, "南"),
    (OrthoViewKind.WEST, "西"),
    (OrthoViewKind.EAST, "东"),
    (OrthoViewKind.TOP_NE, "东北↘"),
    (OrthoViewKind.TOP_SE, "东南↙"),
    (OrthoViewKind.TOP_SW, "西南↖"),
    (OrthoViewKind.TOP_NW, "西北↗"),
]


class _FlakeRasterThread(QThread):
    result_ready = Signal(object, object, str)  # QImage | None, note: str, err: str

    def __init__(
        self,
        path: Path,
        region_name: str,
        kind: OrthoViewKind,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._path = path.resolve()
        self._region_name = region_name
        self._kind = kind

    def run(self) -> None:  # type: ignore[override]
        try:
            data, w, h, note = render_region_ortho_rgba(self._path, self._region_name, self._kind)
        except Exception as exc:
            self.result_ready.emit(None, "", str(exc))
            return
        if data is None or w <= 0 or h <= 0:
            self.result_ready.emit(None, "", note or "渲染失败。")
            return
        stride = w * 4
        img = QImage(data, w, h, stride, QImage.Format.Format_RGBA8888).copy()
        self.result_ready.emit(img, note, "")


class _ScaledPreviewLabel(QLabel):
    """在滚动区内随宽度缩放显示位图，保持长宽比（邻近采样，避免糊边）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._src: QImage | None = None
        self.setMinimumSize(200, 160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background: palette(base); border: 1px solid palette(mid);")

    def set_source_image(self, image: QImage | None) -> None:
        self._src = image if image is None or image.isNull() else image.copy()
        self._apply_scaled()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._apply_scaled()

    def _apply_scaled(self) -> None:
        if self._src is None or self._src.isNull():
            self.setPixmap(QPixmap())
            return
        m = self.contentsMargins()
        aw = max(1, self.width() - m.left() - m.right())
        ah = max(1, self.height() - m.top() - m.bottom())
        scaled = self._src.scaled(
            aw,
            ah,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.setPixmap(QPixmap.fromImage(scaled))


class FlakePage(QWidget):
    """正交剖面：CPU 后台线程生成位图，供分层分析与导出。"""

    def __init__(self, properties_page: PropertiesPage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._props = properties_page
        self._thread: _FlakeRasterThread | None = None
        self._render_superseded: bool = False
        self._last_image: QImage | None = None
        self._last_note = ""

        self._lbl_path = QLabel("请在「属性」页加载 .litematic。")
        self._lbl_path.setWordWrap(True)

        reg_row = QHBoxLayout()
        reg_row.addWidget(QLabel("子区域："))
        self._region_combo = QComboBox()
        self._region_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._region_combo.currentIndexChanged.connect(self._on_region_changed)
        reg_row.addWidget(self._region_combo, 1)

        dir_box = QGroupBox("观察方向（正交 2D 剖面 / legacy）")
        grid = QGridLayout(dir_box)
        self._view_group = QButtonGroup(self)
        self._view_radios: list[QRadioButton] = []
        for i, (vk, label) in enumerate(_VIEW_LABELS):
            rb = QRadioButton(label)
            rb.setProperty("view_kind", int(vk.value))
            self._view_group.addButton(rb)
            self._view_radios.append(rb)
            grid.addWidget(rb, i // 3, i % 3)
        if self._view_radios:
            self._view_radios[0].setChecked(True)
        self._view_group.buttonClicked.connect(lambda _b: self._schedule_render())

        self._btn_refresh = QPushButton("重新渲染")
        self._btn_refresh.clicked.connect(self._schedule_render)

        btn_row = QHBoxLayout()
        self._btn_material = QPushButton("材料列表（当前区域）")
        self._btn_material.clicked.connect(self._on_material_list)
        self._btn_export = QPushButton("导出 PNG…")
        self._btn_export.clicked.connect(self._on_export_png)
        self._btn_preview = QPushButton("写入属性预览图…")
        self._btn_preview.setToolTip("将当前渲染图裁切并缩放为 140×140 写入属性页预览（需保存属性才写入文件）")
        self._btn_preview.clicked.connect(self._on_write_preview)
        btn_row.addWidget(self._btn_material)
        btn_row.addWidget(self._btn_export)
        btn_row.addWidget(self._btn_preview)
        btn_row.addStretch()

        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setStyleSheet("color: palette(mid);")

        self._preview = _ScaledPreviewLabel()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._preview)
        scroll.setMinimumHeight(280)

        root = QVBoxLayout(self)
        root.addWidget(self._lbl_path)
        root.addLayout(reg_row)
        root.addWidget(dir_box)
        root.addWidget(self._btn_refresh)
        root.addLayout(btn_row)
        root.addWidget(self._status)
        root.addWidget(scroll, 1)

        self._props.active_file_changed.connect(self._on_active_file_changed)

    def _current_view_kind(self) -> OrthoViewKind:
        btn = self._view_group.checkedButton()
        if btn is None:
            return OrthoViewKind.TOP
        raw = btn.property("view_kind")
        try:
            v = int(raw)
        except (TypeError, ValueError):
            return OrthoViewKind.TOP
        for e in OrthoViewKind:
            if int(e.value) == v:
                return e
        return OrthoViewKind.TOP

    def _sync_region_combo(self) -> None:
        self._region_combo.blockSignals(True)
        self._region_combo.clear()
        path = self._props.active_file_path()
        if path is None:
            self._region_combo.blockSignals(False)
            return
        try:
            from litemapy import Schematic

            sch = Schematic.load(str(path))
            keys = list(sch.regions.keys())
        except Exception:
            keys = []
        for k in keys:
            self._region_combo.addItem(k, k)
        self._region_combo.blockSignals(False)

    def _selected_region_name(self) -> str | None:
        if self._region_combo.count() <= 0:
            return None
        d = self._region_combo.currentData()
        return str(d) if d is not None else None

    def _on_active_file_changed(self, _path: str) -> None:
        self._sync_path_label()
        self._sync_region_combo()
        self._schedule_render()

    def _on_region_changed(self, _index: int) -> None:
        self._schedule_render()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._sync_path_label()
        if self._region_combo.count() == 0:
            self._sync_region_combo()
        if self._last_image is None and self._props.active_file_path() is not None:
            self._schedule_render()

    def _sync_path_label(self) -> None:
        p = self._props.active_file_path()
        self._lbl_path.setText(str(p) if p is not None else "请在「属性」页加载 .litematic。")

    def _schedule_render(self) -> None:
        path = self._props.active_file_path()
        region = self._selected_region_name()
        if path is None or region is None:
            self._preview.set_source_image(None)
            self._last_image = None
            self._status.setText("无可用文件或子区域。" if path is None else "该文件没有可渲染的子区域。")
            return

        kind = self._current_view_kind()
        resolved = path.resolve()

        if self._thread is not None and self._thread.isRunning():
            self._render_superseded = True
            self._status.setText("渲染中…（将应用最新一次选择）")
            return

        self._render_superseded = False
        self._status.setText("渲染中…")
        th = _FlakeRasterThread(resolved, region, kind, self)
        self._thread = th
        th.result_ready.connect(self._on_thread_result)
        th.finished.connect(self._on_thread_finished)
        th.start()

    def _on_thread_finished(self) -> None:
        self._thread = None
        if self._render_superseded:
            self._render_superseded = False
            self._schedule_render()

    def _on_thread_result(self, image: QImage | None, note: str, err: str) -> None:
        cur = self._props.active_file_path()
        if cur is None:
            return
        if err:
            self._last_image = None
            self._preview.set_source_image(None)
            self._status.setText(err)
            QMessageBox.warning(self, "剖面", err)
            return
        self._last_image = image
        self._last_note = note
        self._preview.set_source_image(image)
        extra = f" {note}" if note else ""
        self._status.setText(f"完成。{extra}".strip())

    def _on_material_list(self) -> None:
        if self._props.active_file_path() is None:
            QMessageBox.information(self, "材料列表", "请先在「属性」页打开一个投影文件。")
            return
        region = self._selected_region_name()
        MaterialListDialog.open_for_properties(self._props, self, initial_region_name=region)

    def _on_export_png(self) -> None:
        if self._last_image is None or self._last_image.isNull():
            QMessageBox.information(self, "导出", "请先成功渲染一张剖面图。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出剖面图",
            str(Path.home() / "flake_section.png"),
            "PNG (*.png)",
        )
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        if not self._last_image.save(path, "PNG"):
            QMessageBox.warning(self, "导出", "保存失败。")
            return
        QMessageBox.information(self, "导出", f"已保存：\n{path}")

    def _on_write_preview(self) -> None:
        if self._last_image is None or self._last_image.isNull():
            QMessageBox.information(self, "预览图", "请先成功渲染一张剖面图。")
            return
        self._props.apply_render_as_preview(self._last_image)
        QMessageBox.information(
            self,
            "预览图",
            "已写入属性页预览（内存）。请到「属性」页确认并保存文件以写入 PreviewImageData。",
        )
