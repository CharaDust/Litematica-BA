"""管理 misode/mcmeta 多版本下载、清除与应用（选项页「游戏资源」）。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFontMetrics, QMouseEvent, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from litematicaba.ui.content_display.list_table.view import (
    METRO_LIST_ROW_HOVER_COLOR,
    METRO_LIST_ROW_TEXT_COLOR,
)
from litematicaba.ui.theme import current_theme_id
from litematicaba.ui.themes.list_view_supplement import (
    mcmeta_version_table_list_row_height_px,
    mcmeta_version_table_min_height_px,
)

from litematicaba.core.nbt_mcmeta_fetch import (
    McmetaFetchResult,
    McmetaVersionEntry,
    fetch_mcmeta_version_catalog,
    filter_mcmeta_catalog_for_picker,
    latest_stable_release_id_from_catalog,
    remove_versioned_mcmeta_assets,
    run_mcmeta_fetch,
)
from litematicaba.core.nbt_viewer_bundle import mcmeta_dir_complete

_OBJ_APPLY_BTN = "McmetaCellApplyBtn"
_OBJ_OP_BTN = "McmetaCellOpBtn"


class _McmetaMetro10CellHost(QWidget):
    """Metro10 下按钮格：仅用 paintEvent 铺底色响应行悬停，不套 QSS，避免改按钮外观。"""

    def __init__(self) -> None:
        super().__init__()
        self._hover_highlight = False

    def set_hover_highlight(self, on: bool) -> None:
        if self._hover_highlight == on:
            return
        self._hover_highlight = on
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        if self._hover_highlight:
            p.fillRect(self.rect(), METRO_LIST_ROW_HOVER_COLOR)
        else:
            p.fillRect(self.rect(), QColor("#ffffff"))
        p.end()


def _wrap_button_centered(btn: QPushButton, *, metro10_hover_cell: bool = False) -> QWidget:
    """表格单元格内按钮水平、垂直居中。"""
    host: QWidget = _McmetaMetro10CellHost() if metro10_hover_cell else QWidget()
    outer = QVBoxLayout(host)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)
    outer.addStretch(1)
    mid = QHBoxLayout()
    mid.setContentsMargins(0, 0, 0, 0)
    mid.addStretch(1)
    mid.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)
    mid.addStretch(1)
    outer.addLayout(mid)
    outer.addStretch(1)
    return host


class _McmetaMetro10FirstColumnDelegate(QStyledItemDelegate):
    """与 UI 测试页 ``ContentListTableWidget`` / ``ThemedPlainQTableWidget`` 第一列绘制一致：无斑马纹、悬停 #E6E6E6。"""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:  # type: ignore[override]
        if index.column() != 0:
            super().paint(painter, option, index)
            return
        parent = self.parent()
        if not isinstance(parent, QTableWidget):
            super().paint(painter, option, index)
            return
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        hr = getattr(parent, "_mcmeta_metro_hover_row", None)
        row = index.row()
        painter.save()
        painter.setClipRect(opt.rect)
        if hr is not None and row == hr:
            painter.fillRect(opt.rect, METRO_LIST_ROW_HOVER_COLOR)
        painter.setPen(METRO_LIST_ROW_TEXT_COLOR)
        tr = opt.rect.adjusted(4, 0, -4, 0)
        elided = QFontMetrics(opt.font).elidedText(
            opt.text, Qt.TextElideMode.ElideRight, max(1, tr.width())
        )
        painter.drawText(tr, int(opt.displayAlignment), elided)
        painter.restore()


class _McmetaCatalogWorker(QThread):
    finished_ok = Signal(list)
    finished_err = Signal(str)

    def run(self) -> None:  # type: ignore[override]
        try:
            catalog = fetch_mcmeta_version_catalog()
            self.finished_ok.emit(catalog)
        except Exception as exc:
            self.finished_err.emit(str(exc))


class _McmetaFetchWorker(QThread):
    finished_fetch = Signal(object)

    def __init__(self, out_base: Path, version_spec: str | None) -> None:
        super().__init__()
        self._out_base = out_base
        self._version_spec = version_spec

    def run(self) -> None:  # type: ignore[override]
        r = run_mcmeta_fetch(out_base=self._out_base, version_spec=self._version_spec)
        self.finished_fetch.emit(r)


class McmetaVersionPickerDialog(QDialog):
    """表格：版本说明、应用、下载/清除。"""

    apply_requested = Signal(str)
    library_changed = Signal()

    def __init__(
        self,
        assets_base: Path,
        applied_version: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("McmetaVersionPickerDialog")
        self.setWindowTitle("Minecraft 数据资源（mcmeta）")
        self.resize(920, 560)
        self._assets_base = assets_base.resolve()
        self._applied_version = (applied_version or "").strip()
        self._catalog: list[McmetaVersionEntry] = []
        self._rows: list[tuple[str, str | None, str]] = []
        self._catalog_worker: _McmetaCatalogWorker | None = None
        self._fetch_worker: _McmetaFetchWorker | None = None
        self._fetch_busy = False
        self._aborted = False
        self._metro10_chrome = False

        lay = QVBoxLayout(self)
        hint = QLabel(
            "资源按版本分目录保存：minecraft-assets/nbt-viewer/<版本 id>/mcmeta/。"
            "未下载时点击「下载」；下载完成后可「清除」。"
            "预览使用选项中「当前应用」的版本，请点击「应用」。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(mid);")
        lay.addWidget(hint)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("筛选："))
        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("按版本 id 或说明文字过滤…")
        self._filter_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self._filter_edit, 1)
        lay.addLayout(filter_row)

        self._table = QTableWidget()
        self._table.setObjectName("McmetaVersionTable")
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["版本", "", ""])
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(self._table.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self._table.setAutoScroll(False)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(1, 72)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(2, 72)
        app = QApplication.instance()
        tid = current_theme_id(app if isinstance(app, QApplication) else None)
        self._metro10_chrome = tid == "Metro10"
        if self._metro10_chrome:
            self._table._mcmeta_metro_hover_row = None  # type: ignore[attr-defined]
            self._table.setAlternatingRowColors(False)
            self._table.setItemDelegate(_McmetaMetro10FirstColumnDelegate(self._table))
            self._table.setMouseTracking(True)
            self._table.viewport().setMouseTracking(True)
            self._table.viewport().installEventFilter(self)
        else:
            self._table.setAlternatingRowColors(True)
        self._table.setMinimumHeight(mcmeta_version_table_min_height_px(tid))
        self._apply_mcmeta_table_row_heights()
        lay.addWidget(self._table, 1)

        self._status = QLabel("正在加载版本列表…")
        lay.addWidget(self._status)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        lay.addWidget(close_btn)

        self._start_catalog_load()

    def _metro10_set_hover_row(self, row: int | None) -> None:
        if not self._metro10_chrome:
            return
        row = row if row is not None and row >= 0 else None
        if row == getattr(self._table, "_mcmeta_metro_hover_row", None):
            return
        self._table._mcmeta_metro_hover_row = row  # type: ignore[attr-defined]
        for r in range(self._table.rowCount()):
            for c in (1, 2):
                host = self._table.cellWidget(r, c)
                if isinstance(host, _McmetaMetro10CellHost):
                    host.set_hover_highlight(row is not None and r == row)
        self._table.viewport().update()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if self._metro10_chrome and obj is self._table.viewport():
            if event.type() == QEvent.Type.MouseMove and isinstance(event, QMouseEvent):
                r = self._table.rowAt(int(event.position().y()))
                self._metro10_set_hover_row(r if r >= 0 else None)
            elif event.type() == QEvent.Type.Leave:
                self._metro10_set_hover_row(None)
        return super().eventFilter(obj, event)

    def _apply_mcmeta_table_row_heights(self) -> None:
        """QTableWidget 行高需代码设置；与主题列表约定一致（见 list_view_supplement.MCMETA_TABLE_ROW_HEIGHT_PX_BY_THEME）。"""
        app = QApplication.instance()
        tid = current_theme_id(app if isinstance(app, QApplication) else None)
        h = mcmeta_version_table_list_row_height_px(tid)
        if h is None:
            return
        vh = self._table.verticalHeader()
        vh.setDefaultSectionSize(h)
        for r in range(self._table.rowCount()):
            self._table.setRowHeight(r, h)

    def _start_catalog_load(self) -> None:
        self._catalog_worker = _McmetaCatalogWorker()
        self._catalog_worker.finished_ok.connect(self._on_catalog_ready)
        self._catalog_worker.finished_err.connect(self._on_catalog_error)
        self._catalog_worker.start()

    def _is_installed(self, folder_id: str) -> bool:
        return mcmeta_dir_complete(self._assets_base / folder_id / "mcmeta")

    def _build_rows(self) -> None:
        self._rows = []
        sid = latest_stable_release_id_from_catalog(self._catalog)
        if sid:
            self._rows.append(
                (f"★ 推荐：最新稳定正式版（当前解析为 {sid}）", None, sid),
            )
        for e in self._catalog:
            typ_zh = "正式版" if e.type == "release" else "快照"
            stab = "稳定" if e.stable else "非稳定"
            line = f"{e.id}  —  {e.name}  —  data {e.data_version}  —  {typ_zh} / {stab}"
            self._rows.append((line, e.id, e.id))

    def _refresh_table_body(self) -> None:
        if self._metro10_chrome:
            self._table._mcmeta_metro_hover_row = None  # type: ignore[attr-defined]
        self._build_rows()
        self._table.setRowCount(len(self._rows))
        for i, (label, fetch_spec, folder_id) in enumerate(self._rows):
            item = QTableWidgetItem(label)
            item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self._table.setItem(i, 0, item)

            installed = self._is_installed(folder_id)
            if installed:
                apply_btn = QPushButton("应用")
                apply_btn.setObjectName(_OBJ_APPLY_BTN)
                apply_btn.setCheckable(True)
                apply_btn.setAutoExclusive(False)
                apply_btn.setChecked(folder_id.strip() == self._applied_version.strip())
                apply_btn.clicked.connect(lambda _c=False, fd=folder_id: self._on_apply(fd))
                self._table.setCellWidget(
                    i, 1, _wrap_button_centered(apply_btn, metro10_hover_cell=self._metro10_chrome)
                )
            else:
                # Metro10：无「应用」时也要占位控件，否则该格无 _McmetaMetro10CellHost，悬停行无法铺灰底
                self._table.setCellWidget(
                    i, 1, _McmetaMetro10CellHost() if self._metro10_chrome else None
                )

            op_btn = QPushButton("清除" if installed else "下载")
            op_btn.setObjectName(_OBJ_OP_BTN)
            op_btn.setEnabled(not self._fetch_busy)
            op_btn.clicked.connect(lambda _c=False, fd=folder_id, fs=fetch_spec: self._on_operation(fd, fs))
            self._table.setCellWidget(
                i, 2, _wrap_button_centered(op_btn, metro10_hover_cell=self._metro10_chrome)
            )
        self._apply_mcmeta_table_row_heights()
        if self._metro10_chrome:
            self._metro10_set_hover_row(None)
        self._apply_filter()

    def _on_catalog_ready(self, catalog: object) -> None:
        self._catalog_worker = None
        if self._aborted:
            return
        if not isinstance(catalog, list):
            self._on_catalog_error("返回数据无效")
            return
        raw = [e for e in catalog if isinstance(e, McmetaVersionEntry)]
        self._catalog = filter_mcmeta_catalog_for_picker(raw)
        self._status.setText(f"共 {len(self._catalog)} 个可选版本（新 → 旧）")
        self._refresh_table_body()

    def _on_catalog_error(self, msg: str) -> None:
        self._catalog_worker = None
        if self._aborted:
            return
        self._status.setText("加载失败")
        QMessageBox.critical(self, "版本列表", f"无法获取版本目录：\n{msg}")
        self.reject()

    def _apply_filter(self) -> None:
        needle = self._filter_edit.text().strip().lower()
        for i in range(self._table.rowCount()):
            it = self._table.item(i, 0)
            if it is None:
                self._table.setRowHidden(i, True)
                continue
            text = it.text().lower()
            self._table.setRowHidden(i, bool(needle) and needle not in text)

    def _on_apply(self, folder_id: str) -> None:
        if not self._is_installed(folder_id):
            return
        self._applied_version = folder_id.strip()
        self.apply_requested.emit(self._applied_version)
        self._sync_apply_buttons_checked()

    def _sync_apply_buttons_checked(self) -> None:
        for i, (_label, _fetch_spec, folder_id) in enumerate(self._rows):
            host = self._table.cellWidget(i, 1)
            if host is None:
                continue
            btn = host.findChild(QPushButton, _OBJ_APPLY_BTN)
            if btn is not None and btn.isCheckable():
                btn.blockSignals(True)
                btn.setChecked(folder_id.strip() == self._applied_version.strip())
                btn.blockSignals(False)

    def _on_operation(self, folder_id: str, fetch_spec: str | None) -> None:
        if self._fetch_busy:
            return
        if self._is_installed(folder_id):
            self._confirm_clear(folder_id)
            return
        self._start_download(fetch_spec)

    def _confirm_clear(self, folder_id: str) -> None:
        r = QMessageBox.question(
            self,
            "清除资源",
            f"确定删除已下载的游戏资源？\n\n版本目录：{folder_id}\n路径：{self._assets_base / folder_id}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if r != QMessageBox.StandardButton.Yes:
            return
        remove_versioned_mcmeta_assets(self._assets_base, folder_id)
        if folder_id.strip() == self._applied_version:
            self._applied_version = ""
            self.apply_requested.emit("")
        self.library_changed.emit()
        self._refresh_table_body()

    def _start_download(self, fetch_spec: str | None) -> None:
        if self._fetch_worker is not None and self._fetch_worker.isRunning():
            return
        self._fetch_busy = True
        self._refresh_op_buttons_enabled()
        self._fetch_worker = _McmetaFetchWorker(self._assets_base, fetch_spec)
        self._fetch_worker.finished_fetch.connect(self._on_fetch_finished)
        self._fetch_worker.start()

    def _refresh_op_buttons_enabled(self) -> None:
        for i in range(self._table.rowCount()):
            host = self._table.cellWidget(i, 2)
            if host is None:
                continue
            btn = host.findChild(QPushButton, _OBJ_OP_BTN)
            if btn is not None:
                btn.setEnabled(not self._fetch_busy)

    def _on_fetch_finished(self, r: object) -> None:
        self._fetch_worker = None
        self._fetch_busy = False
        if self._aborted:
            if isinstance(r, McmetaFetchResult) and r.ok:
                self.library_changed.emit()
            return
        self._refresh_table_body()
        if not isinstance(r, McmetaFetchResult):
            return
        if r.warning:
            QMessageBox.warning(self, "游戏资源", r.warning)
        if not r.ok:
            QMessageBox.critical(self, "游戏资源", r.message)
            return
        QMessageBox.information(
            self,
            "游戏资源",
            r.message + "\n\n若已应用该版本，请到「渲染」页点击「重新加载 3D」或重启应用。",
        )
        self.library_changed.emit()

    def reject(self) -> None:  # type: ignore[override]
        self._aborted = True
        super().reject()

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._aborted = True
        if self._metro10_chrome:
            self._table.viewport().removeEventFilter(self)
        super().closeEvent(event)
