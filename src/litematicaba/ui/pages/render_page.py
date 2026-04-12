"""渲染页：优先使用内置 vscode-nbt 同源 3D（StructureRenderer + litematicToStructure）；否则回退 Deepslate VoxelRenderer + 九向预设。"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, QUrl, Qt, QSize, Signal
from PySide6.QtGui import QImage, QShowEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStyle,
    QStyleOptionButton,
    QVBoxLayout,
    QWidget,
)

from litematicaba.core.litematic_voxel_export import build_region_voxels_payload
from litematicaba.core.nbt_viewer_bundle import (
    external_nbt_viewer_dir,
    packaged_nbt_viewer_dir,
    resolve_nbt_viewer_html_path,
)
from litematicaba.core.settings import AppSettings
from litematicaba.ui.material_list_dialog import MaterialListDialog
from litematicaba.ui.pages.properties_page import PropertiesPage

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView

    _HAS_WEBENGINE = True
except ImportError:
    _HAS_WEBENGINE = False
    QWebEngineView = None  # type: ignore[misc, assignment]


if _HAS_WEBENGINE and QWebEngineView is not None:

    class _DeepslateWebEngineView(QWebEngineView):
        """避免 QWebEngineView 的 sizeHint/minimumSizeHint 抬高主窗口最小高度。"""

        def minimumSizeHint(self) -> QSize:  # type: ignore[override]
            return QSize(0, 0)

        def sizeHint(self) -> QSize:  # type: ignore[override]
            return QSize(0, 0)

else:
    _DeepslateWebEngineView = None  # type: ignore[misc, assignment]

# 与 design §2.6.3.5 / FR-R.6 及前端 ``lbaSetViewPreset(0..8)`` 一致
# 3×3：西北 北 东北 / 西 顶视 东 / 西南 南 东南
_VIEW_GRID: list[tuple[int, int, int, str, str]] = [
    (0, 0, 8, "西北", "西北（俯视）"),
    (0, 1, 1, "北", "北"),
    (0, 2, 5, "东北", "东北（俯视）"),
    (1, 0, 3, "西", "西"),
    (1, 1, 0, "顶视", "顶视图"),
    (1, 2, 4, "东", "东"),
    (2, 0, 7, "西南", "西南（俯视）"),
    (2, 1, 2, "南", "南"),
    (2, 2, 6, "东南", "东南（俯视）"),
]


def _view_dir_button_square_side(widget: QWidget) -> int:
    """由当前样式与字体推导方形边长，避免写死像素。"""
    st = widget.style()
    fm = widget.fontMetrics()
    fallback = max(fm.height() * 2 + 8, fm.horizontalAdvance("顶视") + 16)
    if st is None:
        return fallback
    opt = QStyleOptionButton()
    opt.initFrom(widget)
    opt.text = "顶视"
    opt.state = QStyle.StateFlag.State_Enabled
    sh = st.sizeFromContents(QStyle.ContentsType.CT_PushButton, opt, QSize(), widget)
    side = max(sh.width(), sh.height(), fm.height() + 8)
    return max(side, fallback)


def _web_resources_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "resources" / "web"


def _viewer_html_path() -> Path:
    return _web_resources_dir() / "deepslate_viewer.html"


_EMPTY_VOXELS_B64 = base64.b64encode(
    json.dumps({"voxels": [], "camDist": 64}, separators=(",", ":")).encode("utf-8")
).decode("ascii")


class _VoxelPayloadThread(QThread):
    result_ready = Signal(object, str)  # dict | None, err

    def __init__(self, path: Path, region_name: str | None, parent: QWidget | None = None) -> None:
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


class _NbtRawFileThread(QThread):
    """读取整份 .litematic 原始字节，供前端 Deepslate ``NbtFile.read``（与 vscode-nbt 一致）。"""

    result_ready = Signal(str, str)  # b64, err

    def __init__(self, path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path = path.resolve()

    def run(self) -> None:  # type: ignore[override]
        try:
            raw = self._path.read_bytes()
        except OSError as exc:
            self.result_ready.emit("", str(exc))
            return
        self.result_ready.emit(base64.b64encode(raw).decode("ascii"), "")


class RenderPage(QWidget):
    """3D 预览：vscode-nbt 同源（若资源齐全）或 Deepslate 体素回退。"""

    def __init__(
        self,
        properties_page: PropertiesPage,
        *,
        app_settings: AppSettings | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._props = properties_page
        self._deepslate_invert_y: bool = (
            bool(app_settings.deepslate_invert_y) if app_settings is not None else False
        )
        self._nbt_html_path, self._nbt_viewer_mode = resolve_nbt_viewer_html_path()
        self._use_nbt_viewer: bool = bool(_HAS_WEBENGINE and self._nbt_html_path is not None)
        self._thread: _VoxelPayloadThread | None = None
        self._nbt_thread: _NbtRawFileThread | None = None
        self._load_superseded: bool = False
        self._pending_b64: str | None = None
        self._pending_nbt_b64: str | None = None
        self._viewer_ready: bool = False
        self._canvas_png_action: str | None = None

        self._lbl_path = QLabel("请在「属性」页加载 .litematic。")
        self._lbl_path.setWordWrap(True)

        self._region_strip = QWidget()
        reg_row = QHBoxLayout(self._region_strip)
        reg_row.addWidget(QLabel("子区域："))
        self._region_combo = QComboBox()
        self._region_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._region_combo.currentIndexChanged.connect(self._on_region_changed)
        reg_row.addWidget(self._region_combo, 1)

        self._dir_box = QGroupBox("观察方向（FR-R.6，相机预设）")
        dir_outer = QVBoxLayout(self._dir_box)
        dir_center_row = QHBoxLayout()
        dir_center_row.addStretch(1)
        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setSpacing(-1)
        st = self.style()
        if st is not None:
            sp = st.pixelMetric(QStyle.PixelMetric.PM_LayoutHorizontalSpacing, None, self)
            if sp > 0:
                grid.setHorizontalSpacing(sp)
                grid.setVerticalSpacing(sp)
        self._view_group = QButtonGroup(self)
        self._view_group.setExclusive(True)
        side = _view_dir_button_square_side(self)
        self._view_dir_buttons: list[QPushButton] = []
        for row, col, preset_id, text, tip in _VIEW_GRID:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("view_preset", preset_id)
            btn.setToolTip(tip)
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            btn.setFixedSize(side, side)
            self._view_group.addButton(btn)
            self._view_dir_buttons.append(btn)
            grid.addWidget(btn, row, col)
        for b in self._view_dir_buttons:
            if int(b.property("view_preset")) == 0:
                b.setChecked(True)
                break
        self._view_group.buttonClicked.connect(lambda _b: self._sync_view_preset_js())
        dir_center_row.addWidget(grid_host, 0, Qt.AlignmentFlag.AlignHCenter)
        dir_center_row.addStretch(1)
        dir_outer.addLayout(dir_center_row)

        self._btn_refresh = QPushButton("重新加载 3D")
        self._btn_refresh.clicked.connect(self._on_refresh_clicked)

        btn_row = QHBoxLayout()
        self._btn_material = QPushButton("材料列表（当前区域）")
        self._btn_material.clicked.connect(self._on_material_list)
        self._btn_export = QPushButton("导出 PNG…")
        self._btn_export.clicked.connect(self._on_export_png)
        self._btn_preview = QPushButton("写入属性预览图…")
        self._btn_preview.setToolTip("从当前 WebGL 画布导出 PNG，裁切并缩放为 140×140 写入属性页预览")
        self._btn_preview.clicked.connect(self._on_write_preview)
        btn_row.addWidget(self._btn_material)
        btn_row.addWidget(self._btn_export)
        btn_row.addWidget(self._btn_preview)
        btn_row.addStretch()

        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setStyleSheet("color: palette(mid);")

        root = QVBoxLayout(self)
        root.addWidget(self._lbl_path)
        root.addWidget(self._region_strip)
        root.addWidget(self._dir_box)
        self._region_strip.setVisible(not self._use_nbt_viewer)
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
            assert _DeepslateWebEngineView is not None
            self._view = _DeepslateWebEngineView()
            self._view.setMinimumSize(0, 0)
            self._view.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding,
            )
            self._view.loadFinished.connect(self._on_view_load_finished)
            if self._use_nbt_viewer:
                html = self._nbt_html_path
            else:
                html = _viewer_html_path()
            if html is not None and html.is_file():
                self._view.load(QUrl.fromLocalFile(str(html.resolve())))
            else:
                self._status.setText(f"缺少内置页面：{html}")
            root.addWidget(self._view, 1)

        self._props.active_file_changed.connect(self._on_active_file_changed)

    def _on_refresh_clicked(self) -> None:
        """重新解析 NBT 查看器入口（外部 data 或合并页），再加载当前投影。"""
        if self._view is not None and _HAS_WEBENGINE:
            p, m = resolve_nbt_viewer_html_path()
            now_nbt = p is not None
            if now_nbt != self._use_nbt_viewer:
                self._use_nbt_viewer = now_nbt
                self._region_strip.setVisible(not now_nbt)
            self._nbt_html_path, self._nbt_viewer_mode = p, m
            if now_nbt and p is not None and p.is_file():
                self._viewer_ready = False
                self._view.load(QUrl.fromLocalFile(str(p.resolve())))
            elif not now_nbt:
                html = _viewer_html_path()
                if html.is_file():
                    self._viewer_ready = False
                    self._view.load(QUrl.fromLocalFile(str(html.resolve())))
        self._schedule_load()

    def apply_deepslate_settings(self, s: AppSettings) -> None:
        """由主窗口在选项变更时调用，同步 WebView 内纵向拖拽符号。"""
        self._deepslate_invert_y = bool(s.deepslate_invert_y)
        if not self._use_nbt_viewer:
            self._push_invert_y_to_webview()

    def _push_invert_y_to_webview(self) -> None:
        if self._view is None or not self._viewer_ready:
            return
        lit = "true" if self._deepslate_invert_y else "false"
        self._view.page().runJavaScript(f"window.lbaSetInvertY({lit});")

    def _current_view_preset(self) -> int:
        btn = self._view_group.checkedButton()
        if btn is None:
            return 0
        raw = btn.property("view_preset")
        try:
            v = int(raw)
        except (TypeError, ValueError):
            return 0
        return max(0, min(8, v))

    def _sync_view_preset_js(self) -> None:
        if self._view is None or not self._viewer_ready:
            return
        p = self._current_view_preset()
        self._view.page().runJavaScript(f"window.lbaSetViewPreset({p});")

    def _inject_b64(self, b64: str) -> None:
        if self._view is None or not self._viewer_ready:
            return
        self._view.page().runJavaScript(f"window.lbaLoadVoxelsB64({json.dumps(b64)});")

    def _inject_nbt_default_tree(self) -> None:
        if self._view is None or not self._viewer_ready:
            return
        empty = json.dumps(
            {
                "name": "",
                "root": {},
                "compression": "none",
                "littleEndian": False,
                "bedrockHeader": None,
            },
            separators=(",", ":"),
        )
        js = (
            "(function(){try{if(window.lbaDispatchNbtViewerInit){"
            f"window.lbaDispatchNbtViewerInit({{type:'default',readOnly:true,content:{empty}}});"
            "}}catch(e){console.error(e);}})();"
        )
        self._view.page().runJavaScript(js)

    def _inject_nbt_structure_b64(self, b64: str) -> None:
        if self._view is None or not self._viewer_ready:
            return
        b64_lit = json.dumps(b64)
        js = (
            "(function(){try{\n"
            f"var b64={b64_lit};"
            "var bin=atob(b64);"
            "var u8=new Uint8Array(bin.length);"
            "for(var i=0;i<bin.length;i++)u8[i]=bin.charCodeAt(i);"
            "var c=window.lbaReadNbtFileToJson(u8);"
            "window.lbaDispatchNbtViewerInit({type:'structure',readOnly:true,content:c});"
            "}catch(e){console.error(e);}"
            "})();"
        )
        self._view.page().runJavaScript(js)

    def _try_inject_pending(self) -> None:
        if self._view is None or not self._viewer_ready:
            return
        if self._use_nbt_viewer:
            if self._pending_nbt_b64 is None:
                return
            pending = self._pending_nbt_b64
            self._pending_nbt_b64 = None
            if pending == "":
                self._inject_nbt_default_tree()
            else:
                self._inject_nbt_structure_b64(pending)
            QTimer.singleShot(250, self._sync_view_preset_js)
            return
        if self._pending_b64 is None:
            return
        b64 = self._pending_b64
        self._pending_b64 = None
        self._inject_b64(b64)
        self._sync_view_preset_js()

    def _on_view_load_finished(self, ok: bool) -> None:
        self._viewer_ready = bool(ok)
        if ok:
            self._try_inject_pending()
            if not self._use_nbt_viewer:
                self._sync_view_preset_js()
                self._push_invert_y_to_webview()
            else:
                self._sync_view_preset_js()
                if self._pending_nbt_b64 is None and self._props.active_file_path() is None:
                    self._inject_nbt_default_tree()
        elif self._view is not None:
            self._status.setText("本地 Web 视图加载失败（请确认 resources/web 下 HTML 与 vendor 脚本齐全）。")

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
        if len(keys) > 1:
            self._region_combo.addItem("全部区域（合并）", None)
        for k in keys:
            self._region_combo.addItem(k, k)
        self._region_combo.blockSignals(False)

    def _payload_region_name(self) -> str | None:
        """传给体素线程：``None`` 表示「全部区域合并」；非 ``None`` 为单区域名。"""
        if self._use_nbt_viewer:
            return None
        d = self._region_combo.currentData()
        if d is None:
            return None
        return str(d)

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
        path = self._props.active_file_path()
        if self._view is None:
            if path is None or self._region_combo.count() <= 0:
                self._status.setText("无可用文件或子区域。" if path is None else "该文件没有可加载的子区域。")
            else:
                self._status.setText("需要 Qt WebEngine 才能加载 3D 体素。")
            return

        if self._use_nbt_viewer:
            if path is None:
                self._pending_nbt_b64 = ""
                self._try_inject_pending()
                self._status.setText("无可用文件。")
                return
            resolved = path.resolve()
            if self._nbt_thread is not None and self._nbt_thread.isRunning():
                self._load_superseded = True
                self._status.setText("读取投影文件中…（将应用最新一次操作）")
                return
            self._load_superseded = False
            self._status.setText("读取投影文件中…")
            nth = _NbtRawFileThread(resolved, self)
            self._nbt_thread = nth
            nth.result_ready.connect(self._on_nbt_thread_result)
            nth.finished.connect(self._on_nbt_thread_finished)
            nth.start()
            return

        if path is None or self._region_combo.count() <= 0:
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
        th = _VoxelPayloadThread(resolved, self._payload_region_name(), self)
        self._thread = th
        th.result_ready.connect(self._on_thread_result)
        th.finished.connect(self._on_thread_finished)
        th.start()

    def _on_nbt_thread_finished(self) -> None:
        self._nbt_thread = None
        if self._load_superseded:
            self._load_superseded = False
            self._schedule_load()

    def _on_nbt_thread_result(self, b64: str, err: str) -> None:
        if self._props.active_file_path() is None:
            return
        if self._view is None:
            return
        if err:
            self._pending_nbt_b64 = ""
            self._try_inject_pending()
            self._status.setText(err)
            QMessageBox.warning(self, "NBT 预览", err)
            return
        self._pending_nbt_b64 = b64
        ver_path = external_nbt_viewer_dir() / "mcmeta" / "version.txt"
        if not ver_path.is_file():
            ver_path = packaged_nbt_viewer_dir() / "mcmeta" / "version.txt"
        extra = ""
        if ver_path.is_file():
            try:
                extra = f"（mcmeta {ver_path.read_text(encoding='utf-8').strip()}）"
            except OSError:
                pass
        mode_hint = (
            f" [{self._nbt_viewer_mode}]"
            if self._nbt_viewer_mode in ("external", "merged")
            else ""
        )
        self._status.setText(f"已加载 vscode-nbt 同源 3D 预览{mode_hint}。{extra}".strip())
        self._try_inject_pending()

    def _on_thread_finished(self) -> None:
        self._thread = None
        if self._load_superseded:
            self._load_superseded = False
            self._schedule_load()

    def _on_thread_result(self, payload: dict | None, err: str) -> None:
        if self._props.active_file_path() is None:
            return
        if self._view is None:
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

    def _grab_canvas_png(self, action: str) -> None:
        if self._view is None or not self._viewer_ready:
            QMessageBox.information(self, "渲染", "Web 视图未就绪，无法导出画布。")
            return
        self._canvas_png_action = action
        if self._use_nbt_viewer:
            js = (
                "(() => { var c = document.querySelector("
                "'canvas.structure-3d:not(.click-detection)'); "
                "if (!c) return ''; try { return c.toDataURL('image/png'); } catch (e) { return ''; } })()"
            )
        else:
            js = (
                "(() => { var c = document.getElementById('c'); "
                "if (!c) return ''; try { return c.toDataURL('image/png'); } catch (e) { return ''; } })()"
            )
        self._view.page().runJavaScript(js, self._on_canvas_data_url)

    def _on_canvas_data_url(self, result: object) -> None:
        action = self._canvas_png_action
        self._canvas_png_action = None
        if action is None:
            return
        if not result:
            QMessageBox.warning(self, "渲染", "无法从画布读取图像。")
            return
        s = str(result)
        prefix = "data:image/png;base64,"
        if not s.startswith(prefix):
            QMessageBox.warning(self, "渲染", "画布返回的数据格式异常。")
            return
        try:
            raw = base64.b64decode(s[len(prefix) :], validate=True)
        except Exception:
            QMessageBox.warning(self, "渲染", "无法解码 PNG 数据。")
            return
        img = QImage.fromData(raw, "PNG")
        if img.isNull():
            QMessageBox.warning(self, "渲染", "无效的 PNG 图像。")
            return
        if action == "export":
            path, _ = QFileDialog.getSaveFileName(
                self,
                "导出渲染图",
                str(Path.home() / "render_preview.png"),
                "PNG (*.png)",
            )
            if not path:
                return
            if not path.lower().endswith(".png"):
                path += ".png"
            if not img.save(path, "PNG"):
                QMessageBox.warning(self, "导出", "保存失败。")
                return
            QMessageBox.information(self, "导出", f"已保存：\n{path}")
        elif action == "preview":
            self._props.apply_render_as_preview(img)
            QMessageBox.information(
                self,
                "预览图",
                "已写入属性页预览（内存）。请到「属性」页确认并保存文件以写入 PreviewImageData。",
            )

    def _on_export_png(self) -> None:
        self._grab_canvas_png("export")

    def _on_write_preview(self) -> None:
        self._grab_canvas_png("preview")

    def _on_material_list(self) -> None:
        if self._props.active_file_path() is None:
            QMessageBox.information(self, "材料列表", "请先在「属性」页打开一个投影文件。")
            return
        region = self._payload_region_name() if self._region_combo.count() > 0 else None
        MaterialListDialog.open_for_properties(self._props, self, initial_region_name=region)
