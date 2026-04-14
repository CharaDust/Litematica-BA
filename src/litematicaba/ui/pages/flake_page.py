"""分层页（design §2.5）：子区域、层级滑条、材料列表；左侧平面切片视图待接入。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QComboBox,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from litematicaba.ui.material_list_dialog import MaterialListDialog
from litematicaba.ui.material_list_scan_prewarmer import MaterialListScanPrewarmer
from litematicaba.ui.pages.properties_page import PropertiesPage


class FlakePage(QWidget):
    """FR-F.1～F.4、F.6：视图区占位 + 子区域 + 层级滑条 + 材料列表。"""

    def __init__(
        self,
        properties_page: PropertiesPage,
        parent: QWidget | None = None,
        *,
        material_scan_prewarmer: MaterialListScanPrewarmer | None = None,
    ) -> None:
        super().__init__(parent)
        self._props = properties_page
        self._material_scan_prewarmer = material_scan_prewarmer

        self._lbl_path = QLabel("请在「属性」页加载 .litematic。")
        self._lbl_path.setWordWrap(True)

        reg_row = QHBoxLayout()
        reg_row.addWidget(QLabel("子区域："))
        self._region_combo = QComboBox()
        self._region_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._region_combo.currentIndexChanged.connect(self._on_region_changed)
        reg_row.addWidget(self._region_combo, 1)

        layer_box = QGroupBox("层级控制（FR-F.6）")
        layer_grid = QGridLayout(layer_box)
        self._layer_slider = QSlider(Qt.Orientation.Horizontal)
        self._layer_slider.setRange(0, 319)
        self._layer_slider.setValue(0)
        self._layer_slider.setToolTip(
            "横向单手柄控制显示层级；与 Deepslate / legacy 平面切片对接前为占位。"
        )
        self._layer_slider.valueChanged.connect(self._on_layer_changed)
        self._layer_value_lbl = QLabel("层 Y = 0")
        layer_grid.addWidget(QLabel("层索引："), 0, 0)
        layer_grid.addWidget(self._layer_slider, 0, 1)
        layer_grid.addWidget(self._layer_value_lbl, 1, 1)

        self._view_placeholder = QLabel(
            "左侧分层渲染视图（FR-F.1）待接入：\n"
            "主路径为 Deepslate 内嵌切片，legacy 为二维平面图像（见 design §2.5.2 / FR-F.5）。"
        )
        self._view_placeholder.setWordWrap(True)
        self._view_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._view_placeholder.setStyleSheet(
            "color: palette(mid); border: 1px solid palette(mid); padding: 16px; min-height: 280px;"
        )

        self._btn_material = QPushButton("材料列表（当前区域）")
        self._btn_material.clicked.connect(self._on_material_list)

        root = QVBoxLayout(self)
        root.addWidget(self._lbl_path)
        root.addLayout(reg_row)
        root.addWidget(layer_box)
        root.addWidget(self._view_placeholder, 1)
        root.addWidget(self._btn_material)

        self._props.active_file_changed.connect(self._on_active_file_changed)

    def _on_layer_changed(self, v: int) -> None:
        self._layer_value_lbl.setText(f"层 Y = {v}")

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

    def _on_region_changed(self, _index: int) -> None:
        pass

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._sync_path_label()
        if self._region_combo.count() == 0:
            self._sync_region_combo()

    def _sync_path_label(self) -> None:
        p = self._props.active_file_path()
        self._lbl_path.setText(str(p) if p is not None else "请在「属性」页加载 .litematic。")

    def _on_material_list(self) -> None:
        if self._props.active_file_path() is None:
            QMessageBox.information(self, "材料列表", "请先在「属性」页打开一个投影文件。")
            return
        region = self._selected_region_name()
        MaterialListDialog.open_for_properties(
            self._props,
            self,
            initial_region_name=region,
            material_scan_prewarmer=self._material_scan_prewarmer,
        )
