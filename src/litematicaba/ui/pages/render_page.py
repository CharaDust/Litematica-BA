"""渲染页：Deepslate WebGL 体素预览（首版经 CDN 加载库；需网络与 Qt WebEngine）。"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from PySide6.QtCore import QThread, QUrl, Qt, Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from litematicaba.core.litematic_voxel_export import build_region_voxels_payload
from litematicaba.ui.material_list_dialog import MaterialListDialog
from litematicaba.ui.pages.properties_page import PropertiesPage

try:
    from PySide6.QtWebEngineCore import QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView

    _HAS_WEBENGINE = True
except ImportError:
    _HAS_WEBENGINE = False
    QWebEngineView = None  # type: ignore[misc, assignment]


def _viewer_html_path() -> Path:
    return Path(__file__).resolve().parents[2] / "resources" / "web" / "deepslate_viewer.html"


_EMPTY_VOXELS_B64 = base64.b64encode(
    json.dumps({"voxels": [], "camDist": 64}, separators=(",", ":")).encode("utf-8")
).decode("ascii")


class _VoxelPayloadThread(QThread):
    result_ready = Signal(object, str)  # dict | None, err

    def __init__(self, path: Path, region_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path = path.resolve()
        self._region_name = region_name

    def run(self) -> None:  # type: ignore[override]
        try:
            payload, err = build_region_voxels_payload(self._path, self._region_name)
        except Exception as exc:
            self.result_ready.emit(None, str(exc))
            return
        if err:
            self.result_ready.emit(None, err)
            return
        self.result_ready.emit(payload, "")


class RenderPage(QWidget):
    """使用 Deepslate ``VoxelRenderer`` 的 3D 旋转预览。"""

    def __init__(self, properties_page: PropertiesPage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._props = properties_page
        self._thread: _VoxelPayloadThread | None = None
        self._load_superseded: bool = False
        self._pending_b64: str | None = None
        self._viewer_ready: bool = False

        self._lbl_path = QLabel("请在「属性」页加载 .litematic。")
        self._lbl_path.setWordWrap(True)

        reg_row = QHBoxLayout()
        reg_row.addWidget(QLabel("子区域："))
        self._region_combo = QComboBox()
        self._region_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._region_combo.currentIndexChanged.connect(self._on_region_changed)
        reg_row.addWidget(self._region_combo, 1)

        self._btn_refresh = QPushButton("重新加载 3D")
        self._btn_refresh.clicked.connect(self._schedule_load)

        btn_row = QHBoxLayout()
        self._btn_material = QPushButton("材料列表（当前区域）")
        self._btn_material.clicked.connect(self._on_material_list)
        btn_row.addWidget(self._btn_material)
        btn_row.addStretch()

        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setStyleSheet("color: palette(mid);")

        root = QVBoxLayout(self)
        root.addWidget(self._lbl_path)
        root.addLayout(reg_row)
        root.addWidget(self._btn_refresh)
        root.addLayout(btn_row)
        root.addWidget(self._status)

        if not _HAS_WEBENGINE or QWebEngineView is None:
            tip = QLabel(
                "未安装 Qt WebEngine 组件，无法显示 3D 预览。\n"
                "请安装与当前 PySide6 版本匹配的 PySide6-WebEngine（或完整 Qt WebEngine 包）。"
            )
            tip.setWordWrap(True)
            tip.setAlignment(Qt.AlignmentFlag.AlignTop)
            root.addWidget(tip, 1)
            self._view = None
        else:
            self._view = QWebEngineView()
            prof = self._view.page().profile()
            prof.settings().setAttribute(
                QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
                True,
            )
            self._view.loadFinished.connect(self._on_view_load_finished)
            html = _viewer_html_path()
            if html.is_file():
                self._view.load(QUrl.fromLocalFile(str(html.resolve())))
            else:
                self._status.setText(f"缺少内置页面：{html}")
            root.addWidget(self._view, 1)

        self._props.active_file_changed.connect(self._on_active_file_changed)

    def _inject_b64(self, b64: str) -> None:
        if self._view is None or not self._viewer_ready:
            return
        self._view.page().runJavaScript(f"window.lbaLoadVoxelsB64({json.dumps(b64)});")

    def _try_inject_pending(self) -> None:
        if self._view is None or not self._viewer_ready or self._pending_b64 is None:
            return
        b64 = self._pending_b64
        self._pending_b64 = None
        self._inject_b64(b64)

    def _on_view_load_finished(self, ok: bool) -> None:
        self._viewer_ready = bool(ok)
        if ok:
            self._try_inject_pending()
        elif self._view is not None:
            self._status.setText("Web 视图加载失败（请检查是否允许本地文件访问远程脚本）。")

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
        self._schedule_load()

    def _on_region_changed(self, _index: int) -> None:
        self._schedule_load()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._sync_path_label()
        if self._region_combo.count() == 0:
            self._sync_region_combo()
        if self._props.active_file_path() is not None:
            self._schedule_load()

    def _sync_path_label(self) -> None:
        p = self._props.active_file_path()
        self._lbl_path.setText(str(p) if p is not None else "请在「属性」页加载 .litematic。")

    def _schedule_load(self) -> None:
        if self._view is None:
            return
        path = self._props.active_file_path()
        region = self._selected_region_name()
        if path is None or region is None:
            self._pending_b64 = _EMPTY_VOXELS_B64
            self._try_inject_pending()
            self._status.setText("无可用文件或子区域。" if path is None else "该文件没有可加载的子区域。")
            return

        resolved = path.resolve()
        if self._thread is not None and self._thread.isRunning():
            self._load_superseded = True
            self._status.setText("准备体素数据中…（将应用最新一次选择）")
            return

        self._load_superseded = False
        self._status.setText("准备体素数据中…")
        th = _VoxelPayloadThread(resolved, region, self)
        self._thread = th
        th.result_ready.connect(self._on_thread_result)
        th.finished.connect(self._on_thread_finished)
        th.start()

    def _on_thread_finished(self) -> None:
        self._thread = None
        if self._load_superseded:
            self._load_superseded = False
            self._schedule_load()

    def _on_thread_result(self, payload: dict | None, err: str) -> None:
        if self._props.active_file_path() is None:
            return
        if err:
            self._pending_b64 = _EMPTY_VOXELS_B64
            self._try_inject_pending()
            self._status.setText(err)
            QMessageBox.warning(self, "3D 渲染", err)
            return
        if payload is None:
            self._pending_b64 = _EMPTY_VOXELS_B64
            self._try_inject_pending()
            self._status.setText("无体素数据。")
            return

        note = str(payload.get("note", "") or "")
        wire: dict[str, object] = {
            "voxels": payload.get("voxels", []),
            "camDist": payload.get("camDist", 64),
        }
        raw = json.dumps(wire, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self._pending_b64 = base64.b64encode(raw).decode("ascii")
        extra = f" {note}" if note else ""
        self._status.setText(f"已加载 Deepslate 体素。{extra}".strip())
        self._try_inject_pending()

    def _on_material_list(self) -> None:
        if self._props.active_file_path() is None:
            QMessageBox.information(self, "材料列表", "请先在「属性」页打开一个投影文件。")
            return
        region = self._selected_region_name()
        MaterialListDialog.open_for_properties(self._props, self, initial_region_name=region)
