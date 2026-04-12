"""从 misode/mcmeta 拉取版本列表，供用户选择要下载的游戏资源版本。"""

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from litematicaba.core.nbt_mcmeta_fetch import (
    McmetaVersionEntry,
    fetch_mcmeta_version_catalog,
    filter_mcmeta_catalog_for_picker,
)

_ROLE_IS_AUTO = Qt.ItemDataRole.UserRole
_ROLE_VERSION_ID = Qt.ItemDataRole.UserRole + 1


class _McmetaCatalogWorker(QThread):
    finished_ok = Signal(list)
    finished_err = Signal(str)

    def run(self) -> None:  # type: ignore[override]
        try:
            catalog = fetch_mcmeta_version_catalog()
            self.finished_ok.emit(catalog)
        except Exception as exc:
            self.finished_err.emit(str(exc))


class McmetaVersionPickerDialog(QDialog):
    """选择 mcmeta 目标版本；返回 ``selected_version_spec()``：`None` 表示最新稳定正式版。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("McmetaVersionPickerDialog")
        self.setWindowTitle("选择 Minecraft 数据版本（mcmeta）")
        self.resize(640, 520)
        self._catalog: list[McmetaVersionEntry] = []
        self._worker: _McmetaCatalogWorker | None = None
        self._aborted = False

        lay = QVBoxLayout(self)
        hint = QLabel(
            "列表来自 misode/mcmeta。仅显示：**当前 data 序号最高的一条**（可为快照）与 **全部稳定版**；"
            "其它快照已隐藏。第一项为「最新稳定正式版」自动解析。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(mid);")
        lay.addWidget(hint)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("筛选："))
        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("按版本 id 或显示名称过滤…")
        self._filter_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self._filter_edit, 1)
        lay.addLayout(filter_row)

        self._list = QListWidget()
        self._list.setObjectName("McmetaVersionPickerList")
        self._list.setAlternatingRowColors(True)
        self._list.itemDoubleClicked.connect(lambda _i: self._try_accept())
        lay.addWidget(self._list, 1)

        self._status = QLabel("正在加载版本列表…")
        lay.addWidget(self._status)

        box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        box.accepted.connect(self._try_accept)
        box.rejected.connect(self.reject)
        self._ok_btn = box.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_btn.setEnabled(False)
        lay.addWidget(box)

        self._start_load()

    def _start_load(self) -> None:
        self._worker = _McmetaCatalogWorker()
        self._worker.finished_ok.connect(self._on_catalog_ready)
        self._worker.finished_err.connect(self._on_catalog_error)
        self._worker.start()

    def _on_catalog_ready(self, catalog: object) -> None:
        self._worker = None
        if self._aborted:
            return
        if not isinstance(catalog, list):
            self._on_catalog_error("返回数据无效")
            return
        raw = [e for e in catalog if isinstance(e, McmetaVersionEntry)]
        self._catalog = filter_mcmeta_catalog_for_picker(raw)
        self._status.setText(f"共 {len(self._catalog)} 个可选版本（新 → 旧）")
        self._list.clear()

        auto_it = QListWidgetItem("★ 推荐：最新稳定正式版（自动）")
        auto_it.setData(_ROLE_IS_AUTO, True)
        self._list.addItem(auto_it)

        for e in self._catalog:
            typ_zh = "正式版" if e.type == "release" else "快照"
            stab = "稳定" if e.stable else "非稳定"
            line = f"{e.id}  —  {e.name}  —  data {e.data_version}  —  {typ_zh} / {stab}"
            it = QListWidgetItem(line)
            it.setData(_ROLE_IS_AUTO, False)
            it.setData(_ROLE_VERSION_ID, e.id)
            self._list.addItem(it)

        self._list.setCurrentRow(0)
        self._ok_btn.setEnabled(True)
        self._apply_filter()

    def _on_catalog_error(self, msg: str) -> None:
        self._worker = None
        if self._aborted:
            return
        self._status.setText("加载失败")
        QMessageBox.critical(self, "版本列表", f"无法获取版本目录：\n{msg}")
        self.reject()

    def _apply_filter(self) -> None:
        needle = self._filter_edit.text().strip().lower()
        for i in range(self._list.count()):
            it = self._list.item(i)
            if it is None:
                continue
            is_auto = bool(it.data(_ROLE_IS_AUTO))
            if is_auto:
                it.setHidden(False)
                continue
            eid = (it.data(_ROLE_VERSION_ID) or "").strip().lower()
            text = it.text().lower()
            ok_needle = (not needle) or (needle in eid) or (needle in text)
            it.setHidden(not ok_needle)

    def _try_accept(self) -> None:
        it = self._list.currentItem()
        if it is None or it.isHidden():
            QMessageBox.information(self, "选择版本", "请选择一个可见的版本。")
            return
        self.accept()

    def selected_version_spec(self) -> str | None:
        """`None`：最新稳定正式版；否则为所选版本 id。"""
        it = self._list.currentItem()
        if it is None:
            return None
        if bool(it.data(_ROLE_IS_AUTO)):
            return None
        vid = it.data(_ROLE_VERSION_ID)
        return str(vid) if vid else None

    def reject(self) -> None:  # type: ignore[override]
        self._aborted = True
        super().reject()

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._aborted = True
        super().closeEvent(event)
