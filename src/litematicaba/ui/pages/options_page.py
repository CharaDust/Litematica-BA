"""选项页（design §2.0.10）。"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from litematicaba.core.settings import VALID_THEMES, AppSettings, save_settings


class OptionsPage(QWidget):
    """主页个性化、主题与侧栏 UI 测试入口开关。"""

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

        g_home = QGroupBox("主页与个性化")
        form_home = QFormLayout(g_home)
        self._name = QLineEdit()
        self._name.setPlaceholderText("User")
        form_home.addRow("用户名：", self._name)

        self._slogan_on = QCheckBox("显示欢迎区标语（第二行）")
        form_home.addRow(self._slogan_on)

        self._slogan_text = QLineEdit()
        form_home.addRow("标语内容：", self._slogan_text)

        self._slogan_pt = QSpinBox()
        self._slogan_pt.setRange(18, 36)
        self._slogan_pt.setSuffix(" pt")
        form_home.addRow("标语字号：", self._slogan_pt)

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
        self._show_tile_grid = QCheckBox("显示磁贴网格（仅影响可拖拽磁贴区域）")
        form_dev.addRow(self._show_tile_grid)
        self._tile_auto_place_preferred_cols = QSpinBox()
        self._tile_auto_place_preferred_cols.setRange(1, 64)
        form_dev.addRow("自动放置磁贴优先列数：", self._tile_auto_place_preferred_cols)
        self._tile_view_right_padding_px = QSpinBox()
        self._tile_view_right_padding_px.setRange(0, 300)
        self._tile_view_right_padding_px.setSuffix(" px")
        form_dev.addRow("磁贴视图右侧留白：", self._tile_view_right_padding_px)

        g_pick = QGroupBox("拣选")
        pick_lay = QVBoxLayout(g_pick)
        self._pick_common_groups = QTableWidget(0, 2)
        self._pick_common_groups.setHorizontalHeaderLabels(["名称", "路径"])
        self._pick_common_groups.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._pick_common_groups.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._pick_common_groups.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._pick_common_groups.horizontalHeader().setStretchLastSection(True)
        pick_lay.addWidget(self._pick_common_groups)
        pick_btn_row = QHBoxLayout()
        self._pick_add_btn = QPushButton("新增…")
        self._pick_edit_btn = QPushButton("编辑…")
        self._pick_rm_btn = QPushButton("删除")
        pick_btn_row.addWidget(self._pick_add_btn)
        pick_btn_row.addWidget(self._pick_edit_btn)
        pick_btn_row.addWidget(self._pick_rm_btn)
        pick_btn_row.addStretch()
        pick_lay.addLayout(pick_btn_row)


        body_lay.addWidget(g_home)
        body_lay.addWidget(g_theme)
        body_lay.addWidget(g_dev)
        body_lay.addWidget(g_pick)
        body_lay.addStretch()

        self._name.textChanged.connect(self._persist)
        self._slogan_on.toggled.connect(self._persist)
        self._slogan_text.textChanged.connect(self._persist)
        self._slogan_pt.valueChanged.connect(self._persist)
        self._theme.currentIndexChanged.connect(self._persist)
        self._show_ui_test.toggled.connect(self._persist)
        self._show_widget_inspector.toggled.connect(self._persist)
        self._show_tile_grid.toggled.connect(self._persist)
        self._tile_auto_place_preferred_cols.valueChanged.connect(self._persist)
        self._tile_view_right_padding_px.valueChanged.connect(self._persist)
        self._pick_add_btn.clicked.connect(self._on_add_pick_group)
        self._pick_edit_btn.clicked.connect(self._on_edit_pick_group)
        self._pick_rm_btn.clicked.connect(self._on_remove_pick_group)

        self._loading = False

    def load(self, s: AppSettings) -> None:
        self._loading = True
        self._name.setText(s.display_name)
        self._slogan_on.setChecked(s.slogan_visible)
        self._slogan_text.setText(s.slogan_text)
        self._slogan_pt.setValue(s.slogan_pt)
        idx = self._theme.findData(s.theme_id)
        self._theme.setCurrentIndex(max(0, idx))
        self._show_ui_test.setChecked(s.show_ui_test_nav)
        self._show_widget_inspector.setChecked(s.show_widget_inspector)
        self._show_tile_grid.setChecked(s.show_tile_grid)
        self._tile_auto_place_preferred_cols.setValue(s.tile_auto_place_preferred_cols)
        self._tile_view_right_padding_px.setValue(s.tile_view_right_padding_px)
        self._pick_common_groups.setRowCount(0)
        for group in s.pick_common_groups:
            self._append_pick_group_row(group["name"], group["path"])
        self._loading = False

    def current_settings(self) -> AppSettings:
        return AppSettings(
            display_name=self._name.text(),
            slogan_visible=self._slogan_on.isChecked(),
            slogan_text=self._slogan_text.text(),
            slogan_pt=self._slogan_pt.value(),
            theme_id=self._theme.currentData(),
            show_ui_test_nav=self._show_ui_test.isChecked(),
            show_widget_inspector=self._show_widget_inspector.isChecked(),
            show_tile_grid=self._show_tile_grid.isChecked(),
            tile_auto_place_preferred_cols=self._tile_auto_place_preferred_cols.value(),
            tile_view_right_padding_px=self._tile_view_right_padding_px.value(),
            pick_common_groups=self._collect_pick_common_groups(),
        ).normalized()

    def _persist(self) -> None:
        if self._loading:
            return
        s = self.current_settings()
        save_settings(s)
        self.settings_changed.emit(s)

    def _append_pick_group_row(self, name: str, path: str) -> None:
        row = self._pick_common_groups.rowCount()
        self._pick_common_groups.insertRow(row)
        self._pick_common_groups.setItem(row, 0, QTableWidgetItem(name))
        self._pick_common_groups.setItem(row, 1, QTableWidgetItem(path))

    def _collect_pick_common_groups(self) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for row in range(self._pick_common_groups.rowCount()):
            name_item = self._pick_common_groups.item(row, 0)
            path_item = self._pick_common_groups.item(row, 1)
            name = (name_item.text() if name_item else "").strip()
            path = (path_item.text() if path_item else "").strip()
            if name and path:
                out.append({"name": name, "path": path})
        return out

    def _edit_pick_group_dialog(self, name: str = "", path: str = "") -> tuple[str, str] | None:
        dlg = QDialog(self)
        dlg.setWindowTitle("常用分类组")
        name_edit = QLineEdit(name)
        path_edit = QLineEdit(path)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        fl = QFormLayout(dlg)
        fl.addRow("名称", name_edit)
        fl.addRow("路径", path_edit)
        fl.addWidget(bb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        n = name_edit.text().strip()
        p = path_edit.text().strip()
        if not n or not p:
            QMessageBox.warning(self, "常用分类组", "名称和路径都不能为空。")
            return None
        return n, p

    def _on_add_pick_group(self) -> None:
        result = self._edit_pick_group_dialog()
        if result is None:
            return
        self._append_pick_group_row(*result)
        self._persist()

    def _on_edit_pick_group(self) -> None:
        row = self._pick_common_groups.currentRow()
        if row < 0:
            QMessageBox.information(self, "常用分类组", "请先选择一条要编辑的记录。")
            return
        name_item = self._pick_common_groups.item(row, 0)
        path_item = self._pick_common_groups.item(row, 1)
        result = self._edit_pick_group_dialog(
            name_item.text() if name_item else "",
            path_item.text() if path_item else "",
        )
        if result is None:
            return
        self._pick_common_groups.setItem(row, 0, QTableWidgetItem(result[0]))
        self._pick_common_groups.setItem(row, 1, QTableWidgetItem(result[1]))
        self._persist()

    def _on_remove_pick_group(self) -> None:
        row = self._pick_common_groups.currentRow()
        if row < 0:
            return
        self._pick_common_groups.removeRow(row)
        self._persist()
