"""启动后或切换「应用到材料列表」图标包后，在后台遍历 PNG 并在主线程小批量解码进 pixmap 缓存。"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPixmap

from litematicaba.core.game_resource_block_icon import (
    ensure_initial_block_2d_seeded,
    material_list_icon_resolution_tag,
    material_list_icon_search_root,
)
from litematicaba.core.material_list_icon_pixmap_cache import store_prewarmed_scaled_pixmap

_ATTACHED: MaterialListIconPrewarmer | None = None
_MATERIAL_UI_ICON_PREWARM_HOOK: Callable[[], None] | None = None


def register_material_ui_icon_prewarm_hook(fn: Callable[[], None] | None) -> None:
    """主窗口登记：在首次打开材料列表或进入分层页时触发（由设置决定是否真启动预载）。"""
    global _MATERIAL_UI_ICON_PREWARM_HOOK
    _MATERIAL_UI_ICON_PREWARM_HOOK = fn


def request_icon_prewarm_from_material_or_flake_ui() -> None:
    if _MATERIAL_UI_ICON_PREWARM_HOOK is not None:
        _MATERIAL_UI_ICON_PREWARM_HOOK()

# 主线程单次只解码少量 PNG，定时器间隔让出事件循环，避免长时间「未响应」。
_DECODE_SLICE = 10
_DECODE_GAP_MS = 8
_WORKER_BATCH = 32


def attach_material_list_icon_prewarmer(p: MaterialListIconPrewarmer) -> None:
    global _ATTACHED
    _ATTACHED = p


def restart_material_list_icon_prewarm() -> None:
    if _ATTACHED is not None:
        _ATTACHED.restart()


class _CollectPngBytesThread(QThread):
    batch_ready = Signal(str, object)  # tag, list[tuple[str, bytes]]
    done_tag = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    def run(self) -> None:  # type: ignore[override]
        # 重 IO / 首次种子化放在工作线程，避免启动后卡死 GUI。
        ensure_initial_block_2d_seeded()
        root = material_list_icon_search_root()
        if not root.is_dir():
            self.done_tag.emit("")
            return
        tag = material_list_icon_resolution_tag()
        batch: list[tuple[str, bytes]] = []
        seen: set[str] = set()
        try:
            for p in root.rglob("*.png"):
                if self.isInterruptionRequested():
                    return
                stem = p.stem
                if not stem or stem in seen:
                    continue
                try:
                    data = p.read_bytes()
                except OSError:
                    continue
                seen.add(stem)
                batch.append((stem, data))
                if len(batch) >= _WORKER_BATCH:
                    self.batch_ready.emit(tag, batch)
                    batch = []
            if batch:
                self.batch_ready.emit(tag, batch)
        finally:
            self.done_tag.emit(tag)


class MaterialListIconPrewarmer(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._worker: _CollectPngBytesThread | None = None
        self._decode_queue: deque[tuple[str, list[tuple[str, bytes]]]] = deque()
        self._active_list: list[tuple[str, bytes]] | None = None
        self._active_i: int = 0
        self._timer = QTimer(self)
        self._timer.setInterval(_DECODE_GAP_MS)
        self._timer.timeout.connect(self._pump_decode_slice)

    def stop(self) -> None:
        """停止后台读盘与主线程解码队列。"""
        if self._worker is not None:
            self._worker.requestInterruption()
            self._worker = None
        self._decode_queue.clear()
        self._active_list = None
        self._active_i = 0
        self._timer.stop()

    def start(self) -> None:
        self.stop()
        w = _CollectPngBytesThread(self)
        self._worker = w
        w.batch_ready.connect(self._on_worker_batch)
        w.done_tag.connect(self._on_worker_done_tag)
        w.start()

    def restart(self) -> None:
        self.stop()
        self.start()

    def _on_worker_batch(self, tag: str, items: object) -> None:
        if not isinstance(items, list):
            return
        self._decode_queue.append((tag, items))
        if not self._timer.isActive():
            self._timer.start()

    def _on_worker_done_tag(self, _tag: str) -> None:
        self._worker = None

    def _pump_decode_slice(self) -> None:
        cur = material_list_icon_resolution_tag()
        decoded = 0
        while decoded < _DECODE_SLICE:
            if self._active_list is None:
                if not self._decode_queue:
                    self._timer.stop()
                    return
                tag, batch = self._decode_queue.popleft()
                if tag != cur:
                    continue
                self._active_list = batch
                self._active_i = 0

            if material_list_icon_resolution_tag() != cur:
                self._active_list = None
                self._active_i = 0
                cur = material_list_icon_resolution_tag()
                continue

            if self._active_i >= len(self._active_list):
                self._active_list = None
                self._active_i = 0
                continue

            stem, data = self._active_list[self._active_i]
            self._active_i += 1
            if isinstance(stem, str) and isinstance(data, (bytes, bytearray)):
                img = QImage.fromData(bytes(data))
                if not img.isNull():
                    pm = QPixmap.fromImage(
                        img.scaled(
                            32,
                            32,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.FastTransformation,
                        )
                    )
                    store_prewarmed_scaled_pixmap(stem, pm)
            decoded += 1
