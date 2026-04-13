"""材料列表独立窗口（design §2.8）：缓存优先、异步刷新；图标列为 32×32 占位。"""

from __future__ import annotations

import csv
from datetime import datetime
from itertools import chain
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPalette, QPixmap, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from litematicaba.core.config import project_root
from litematicaba.core.litematic_block_scan import scan_litematic_block_counts, sorted_block_counts
from litematicaba.core.snbt_properties import load_snbt_properties
from litematicaba.core.material_list_cache import (
    cache_is_stale,
    file_mtime_ns,
    load_material_cache,
    save_material_cache,
)
from litematicaba.ui.pages.properties_page import PropertiesPage

_PLACEHOLDER_PM: QPixmap | None = None

# 材料列表导出：仅 Item + Total 两列（CSV / ASCII 文本表）
_MIN_ITEM_W = 7
_MIN_NUM_W = 7


def _placeholder_32() -> QPixmap:
    global _PLACEHOLDER_PM
    if _PLACEHOLDER_PM is None or _PLACEHOLDER_PM.isNull():
        pm = QPixmap(32, 32)
        pm.fill(QColor(120, 120, 120, 90))
        _PLACEHOLDER_PM = pm
    return _PLACEHOLDER_PM


def _load_block_cn_map() -> dict[str, str]:
    import json

    path = project_root() / "lang" / "setting.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    b = raw.get("Blocks")
    if not isinstance(b, dict):
        return {}
    return {str(k): str(v) for k, v in b.items()}


def _display_name(block_id: str, cn: dict[str, str]) -> str:
    if block_id.startswith("E/"):
        return block_id
    raw = block_id.split("[")[0].strip()
    if ":" in raw:
        local = raw.split(":", 1)[1]
    else:
        local = raw
    return cn.get(local, raw)


_WIN_INVALID_FS = '<>:"/\\|?*\n\r\t'


def _filename_safe_segment(name: str) -> str:
    t = "".join(c if c not in _WIN_INVALID_FS else "_" for c in name)
    t = t.strip(" .")
    return t or "export"


def _litematic_internal_metadata_names(path: Path) -> tuple[str, str]:
    """读取 ``Metadata.Name``：返回 (用于标题等展示, 用于文件名的安全段)。"""
    try:
        raw = load_snbt_properties(path).internal_name.strip()
    except Exception:
        raw = ""
    display = raw if raw else "未命名"
    return display, _filename_safe_segment(display)


def _material_list_suggested_save_path(*, internal_segment: str, extension: str) -> str:
    """material_list_<内部名安全段>_<YYYY-MM-DD>_<HH.MM.SS>.<ext>，置于用户主目录下作为初始路径。"""
    ext = extension if extension.startswith(".") else f".{extension}"
    stamp = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
    return str(Path.home() / f"material_list_{internal_segment}_{stamp}{ext}")


def _material_list_export_title(
    *,
    litematic_path: Path | None,
    region_name: str | None,
    csv_source: Path | None,
    litematic_quoted_name: str | None = None,
) -> str:
    if litematic_path is not None:
        name = (
            litematic_quoted_name
            if litematic_quoted_name is not None
            else _litematic_internal_metadata_names(litematic_path)[0]
        )
        if region_name is None:
            return f"原理图的材料清单 '{name}' (1 of 1 区域)"
        return f"原理图的材料清单 '{name}' (选定区域：{region_name})"
    if csv_source is not None:
        return f"原理图的材料清单 '{csv_source.stem}' (自定义文件)"
    return "原理图的材料清单"


def _material_list_txt_table(title: str, rows_display: list[tuple[str, int]]) -> str:
    """ASCII 表格：Item | Total 两列（与 CSV 含义一致）。"""
    w_item = max(_MIN_ITEM_W, len("Item"), max(len(r[0]) for r in rows_display) if rows_display else 0)
    w_tot = max(_MIN_NUM_W, len("Total"), max(len(str(r[1])) for r in rows_display) if rows_display else 0)

    title_inner = w_item + 1 + w_tot
    sep = "+" + "-" * w_item + "+" + "-" * w_tot + "+"

    def txt_cell_text(s: str, w: int) -> str:
        return (" " + str(s).strip())[:w].ljust(w)

    def row_header(a: str, b: str) -> str:
        return "|" + txt_cell_text(a, w_item) + "|" + txt_cell_text(b, w_tot) + "|"

    def row_data(item: str, tot: int) -> str:
        c_item = (" " + str(item).strip())[:w_item].ljust(w_item)
        return "|" + c_item + "|" + str(tot).rjust(w_tot) + "|"

    title_pad = (" " + title.strip())[:title_inner].ljust(title_inner)
    lines = [
        sep,
        "|" + title_pad + "|",
        sep,
        row_header("Item", "Total"),
        sep,
    ]
    for item, total in rows_display:
        lines.append(row_data(item, total))
    lines.extend(
        [
            sep,
            row_header("Item", "Total"),
            sep,
        ]
    )
    return "\n".join(lines) + "\n"


class _MaterialScanThread(QThread):
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(
        self,
        path: Path,
        *,
        region_name: str | None,
        include_entities: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._path = path.resolve()
        self._region = region_name
        self._inc = include_entities

    def run(self) -> None:  # type: ignore[override]
        try:
            d = scan_litematic_block_counts(
                self._path,
                include_entities=self._inc,
                region_name=self._region,
            )
            self.finished_ok.emit(d)
        except Exception as exc:
            self.failed.emit(str(exc))


class MaterialListDialog(QDialog):
    """非模态材料列表；依赖 ``PropertiesPage`` 获取当前激活路径。"""

    def __init__(
        self,
        properties_page: PropertiesPage,
        parent: QWidget | None = None,
        *,
        initial_region_name: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("材料列表")
        self.setMinimumSize(560, 420)
        self.setModal(False)
        self._props = properties_page
        self._cn = _load_block_cn_map()
        self._thread: _MaterialScanThread | None = None
        self._base_rows: list[tuple[str, int]] = []
        self._litematic_path: Path | None = None
        self._region_name: str | None = None
        self._csv_mode = False
        self._csv_source: Path | None = None
        self._pending_queue: bool = False
        self._table_gray: bool = False

        top = QHBoxLayout()
        self._workbook = QComboBox()
        self._workbook.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._workbook.currentIndexChanged.connect(self._on_workbook_changed)
        top.addWidget(QLabel("工作簿："))
        top.addWidget(self._workbook, 1)

        btn_row = QHBoxLayout()
        self._btn_reload = QPushButton("重新加载")
        self._btn_reload.clicked.connect(self._on_reload_clicked)
        self._btn_export = QPushButton("写入文件…")
        self._btn_export.clicked.connect(self._on_export_clicked)
        self._spin_mult = QSpinBox()
        self._spin_mult.setRange(1, 999_999)
        self._spin_mult.setValue(1)
        self._spin_mult.setPrefix("倍数 ")
        self._spin_mult.valueChanged.connect(self._refresh_multiplier_only)
        self._cb_entities = QCheckBox("统计实体")
        self._cb_entities.toggled.connect(self._on_entities_toggled)
        btn_row.addWidget(self._btn_reload)
        btn_row.addWidget(self._btn_export)
        btn_row.addWidget(self._spin_mult)
        btn_row.addStretch()
        btn_row.addWidget(self._cb_entities)

        self._status = QLabel("")
        self._status.setStyleSheet("color: palette(mid);")

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["图标", "名称", "总计"])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setColumnWidth(0, 40)
        self._table.horizontalHeader().setStretchLastSection(True)

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addLayout(btn_row)
        root.addWidget(self._status)
        root.addWidget(self._table, 1)

        self._reload_from_context()
        if initial_region_name:
            self._select_workbook_region(initial_region_name)

    def _select_workbook_region(self, name: str) -> None:
        self._workbook.blockSignals(True)
        idx = 0
        for i in range(self._workbook.count()):
            if self._workbook.itemData(i) == name:
                idx = i
                break
        self._workbook.setCurrentIndex(idx)
        self._workbook.blockSignals(False)
        self._apply_workbook_selection(force_refresh=False)

    def _fill_region_items(self, region_keys: list[str]) -> None:
        self._workbook.blockSignals(True)
        self._workbook.clear()
        self._workbook.addItem("整个投影", None)
        for k in region_keys:
            self._workbook.addItem(f"选定区域：{k}", k)
        self._workbook.addItem("选定层级（需分层模块）", "__DISABLED__")
        d_idx = self._workbook.count() - 1
        m = self._workbook.model()
        if isinstance(m, QStandardItemModel):
            it = m.item(d_idx)
            if it is not None:
                it.setEnabled(False)
        self._workbook.addItem("自定义文件…", "__CSV__")
        self._workbook.blockSignals(False)

    def _reload_from_context(self, *, force_refresh: bool = False) -> None:
        path = self._props.active_file_path()
        if path is None:
            self._status.setText("无激活投影文件。")
            self._table.setRowCount(0)
            self._litematic_path = None
            return
        self._litematic_path = path.resolve()
        self._csv_mode = False
        self._csv_source = None
        self._sync_region_combo_from_file()
        self._apply_workbook_selection(force_refresh=force_refresh)

    def _sync_region_combo_from_file(self) -> None:
        path = self._props.active_file_path()
        if path is None:
            return
        try:
            from litemapy import Schematic

            sch = Schematic.load(str(path))
            keys = list(sch.regions.keys())
        except Exception:
            keys = []
        self._fill_region_items(keys)

    def _current_region_param(self) -> str | None:
        data = self._workbook.currentData()
        if data is None:
            return None
        if isinstance(data, str) and data in ("__DISABLED__", "__CSV__"):
            return None
        if isinstance(data, str):
            return data
        return None

    def _on_workbook_changed(self, index: int) -> None:
        if index < 0:
            return
        data = self._workbook.itemData(index)
        if data == "__CSV__":
            self._workbook.blockSignals(True)
            path, _ = QFileDialog.getOpenFileName(
                self,
                "选择材料列表 CSV",
                "",
                "CSV (*.csv);;All (*.*)",
            )
            if path:
                self._load_csv_counts(Path(path))
            else:
                self._workbook.setCurrentIndex(0)
            self._workbook.blockSignals(False)
            return
        if data == "__DISABLED__":
            self._workbook.blockSignals(True)
            self._workbook.setCurrentIndex(0)
            self._workbook.blockSignals(False)
            return
        self._csv_mode = False
        self._csv_source = None
        self._region_name = self._current_region_param()
        self._start_material_flow()

    def _load_csv_counts(self, csv_path: Path) -> None:
        try:
            counts: dict[str, int] = {}
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                r = csv.reader(f)
                rows_iter = iter(r)
                first = next(rows_iter, None)
                total_col = 1
                if first and len(first) >= 2 and first[0].strip().lower() == "item":
                    try:
                        total_col = next(
                            i for i, c in enumerate(first) if c.strip().lower() == "total"
                        )
                    except StopIteration:
                        total_col = 1
                    data_rows = rows_iter
                else:
                    data_rows = chain([] if first is None else [first], rows_iter)
                for row in data_rows:
                    if len(row) <= total_col:
                        continue
                    key = row[0].strip()
                    if not key or key.lower() in ("id", "block", "方块", "名称", "item", "block_id"):
                        continue
                    try:
                        counts[key] = counts.get(key, 0) + int(float(row[total_col]))
                    except ValueError:
                        continue
        except OSError as exc:
            QMessageBox.warning(self, "CSV", f"读取失败：{exc}")
            self._workbook.setCurrentIndex(0)
            return
        self._csv_mode = True
        self._csv_source = csv_path
        self._litematic_path = None
        self._base_rows = sorted_block_counts(counts)
        self._status.setText(f"自定义文件：{csv_path.name}")
        self._fill_table(self._base_rows, gray=False)

    def _apply_workbook_selection(self, *, force_refresh: bool = False) -> None:
        self._region_name = self._current_region_param()
        self._start_material_flow(force_refresh=force_refresh)

    def _on_reload_clicked(self) -> None:
        if self._csv_mode and self._csv_source is not None:
            self._load_csv_counts(self._csv_source)
            return
        self._reload_from_context(force_refresh=True)

    def _on_entities_toggled(self, _on: bool) -> None:
        if not self._csv_mode:
            self._start_material_flow(force_refresh=True)

    def _start_material_flow(self, *, force_refresh: bool = False) -> None:
        if self._csv_mode:
            return
        path = self._props.active_file_path()
        if path is None:
            return
        resolved = path.resolve()
        inc = self._cb_entities.isChecked()
        region = self._region_name

        if self._thread is not None and self._thread.isRunning():
            self._pending_queue = True
            return

        cached = None if force_refresh else load_material_cache(resolved, region_name=region, include_entities=inc)
        if cached is not None:
            counts, mns = cached
            stale = cache_is_stale(resolved, mns)
            self._base_rows = sorted_block_counts(counts)
            self._fill_table(self._base_rows, gray=stale)
            self._status.setText("已显示缓存" + ("（文件已变更，后台刷新中…）" if stale else "（后台校验中…）"))
        else:
            self._status.setText("正在扫描投影…")
            self._table.setRowCount(0)

        self._thread = _MaterialScanThread(
            resolved,
            region_name=region,
            include_entities=inc,
            parent=self,
        )
        self._thread.finished_ok.connect(self._on_scan_done)
        self._thread.failed.connect(self._on_scan_failed)
        self._thread.finished.connect(self._on_scan_thread_finished)
        self._thread.start()

    def _on_scan_thread_finished(self) -> None:
        self._thread = None
        if self._pending_queue:
            self._pending_queue = False
            self._start_material_flow(force_refresh=True)

    def _on_scan_done(self, counts: dict) -> None:
        th = self.sender()
        if not isinstance(th, _MaterialScanThread):
            return
        expected = th._path
        path = self._props.active_file_path()
        if path is None or path.resolve() != expected:
            return
        if th._region != self._region_name or th._inc != self._cb_entities.isChecked():
            return
        try:
            mns = file_mtime_ns(path)
            save_material_cache(
                path.resolve(),
                region_name=th._region,
                include_entities=th._inc,
                counts=dict(counts),
                mtime_ns=mns,
            )
        except OSError:
            pass
        self._base_rows = sorted_block_counts(dict(counts))
        self._fill_table(self._base_rows, gray=False)
        self._status.setText("已更新为最新扫描结果。")

    def _on_scan_failed(self, msg: str) -> None:
        self._status.setText(msg)
        QMessageBox.warning(self, "材料列表", msg)

    def _fill_table(self, rows: list[tuple[str, int]], *, gray: bool) -> None:
        self._table_gray = gray
        mult = self._spin_mult.value()
        if gray:
            brush = QBrush(QColor(140, 140, 140))
        else:
            brush = self._table.palette().brush(QPalette.ColorRole.Text)
        self._table.setRowCount(len(rows))
        pm = _placeholder_32()
        for i, (bid, cnt) in enumerate(rows):
            icon_label = QLabel()
            icon_label.setPixmap(pm)
            icon_label.setFixedSize(32, 32)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setCellWidget(i, 0, icon_label)

            name_item = QTableWidgetItem(_display_name(bid, self._cn))
            name_item.setForeground(brush)
            name_item.setData(Qt.ItemDataRole.UserRole, bid)
            self._table.setItem(i, 1, name_item)

            total_item = QTableWidgetItem(str(cnt * mult))
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            total_item.setForeground(brush)
            self._table.setItem(i, 2, total_item)
            self._table.setRowHeight(i, 36)

    def _refresh_multiplier_only(self) -> None:
        if not self._base_rows:
            return
        self._fill_table(self._base_rows, gray=self._table_gray)

    def _on_export_clicked(self) -> None:
        if not self._base_rows:
            QMessageBox.information(self, "写入文件", "没有可导出的数据。")
            return
        internal_seg = "export"
        lit_display: str | None = None
        if self._litematic_path is not None:
            lit_display, internal_seg = _litematic_internal_metadata_names(self._litematic_path)
        elif self._csv_source is not None:
            internal_seg = _filename_safe_segment(self._csv_source.stem)
        suggested = _material_list_suggested_save_path(internal_segment=internal_seg, extension=".csv")
        path, filt = QFileDialog.getSaveFileName(
            self,
            "导出材料列表",
            suggested,
            "逗号分隔 (*.csv);;文本 (*.txt)",
        )
        if not path:
            return
        mult = self._spin_mult.value()
        rows = [(b, c * mult) for b, c in self._base_rows]
        title = _material_list_export_title(
            litematic_path=self._litematic_path,
            region_name=self._region_name,
            csv_source=self._csv_source,
            litematic_quoted_name=lit_display,
        )
        display_rows = [(_display_name(bid, self._cn), cnt) for bid, cnt in rows]
        try:
            if filt.startswith("逗号") or path.lower().endswith(".csv"):
                if not path.lower().endswith(".csv"):
                    path += ".csv"
                with open(path, "w", newline="", encoding="utf-8-sig") as f:
                    w = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
                    w.writerow(["Item", "Total"])
                    for item, total in display_rows:
                        w.writerow([item, total])
            else:
                if not path.lower().endswith(".txt"):
                    path += ".txt"
                Path(path).write_text(
                    _material_list_txt_table(title, display_rows),
                    encoding="utf-8",
                )
        except OSError as exc:
            QMessageBox.warning(self, "写入失败", str(exc))
            return
        QMessageBox.information(self, "写入文件", f"已保存到：\n{path}")

    @staticmethod
    def open_for_properties(
        properties_page: PropertiesPage,
        parent: QWidget | None = None,
        *,
        initial_region_name: str | None = None,
    ) -> MaterialListDialog:
        dlg = MaterialListDialog(
            properties_page,
            parent,
            initial_region_name=initial_region_name,
        )
        dlg.show()
        return dlg
