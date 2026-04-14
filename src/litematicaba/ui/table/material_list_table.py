"""材料列表对话框内 ``QTableWidget``：列表型 ``table_list_hover_bg`` / ``table_list_selected_bg``（delegate + 图标列同步）。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QModelIndex, QObject, Qt
from PySide6.QtGui import QColor, QFontMetrics, QMouseEvent, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QTableWidget

from litematicaba.ui.table.metro10_list_profile import (
    METRO10_LIST_TABLE_TOKENS,
    apply_metro_list_flat_chrome_flags,
    content_list_row_height_px,
    is_metro_list_table_theme,
)
from litematicaba.ui.table.minecraft_list_profile import (
    MINECRAFT_LIST_TABLE_TOKENS,
    apply_minecraft_content_list_chrome_flags,
    apply_minecraft_list_table_header_chrome,
    is_minecraft_list_table_theme,
)
from litematicaba.ui.theme import normalize_theme_id
from litematicaba.ui.themes.base import icon_dir
from litematicaba.ui.widgets.mcmeta_standard_table import apply_mcmeta_table_viewport_fill_below_items

_BLOCK_ICON_PM: QPixmap | None = None


def material_list_block_icon_pixmap_32() -> QPixmap:
    """材料列表图标列占位：``resources/icon/block_example.png`` 缩放到 32×32。"""
    global _BLOCK_ICON_PM
    if _BLOCK_ICON_PM is not None and not _BLOCK_ICON_PM.isNull():
        return _BLOCK_ICON_PM
    path = icon_dir() / "block_example.png"
    pm = QPixmap(str(path))
    if pm.isNull():
        fb = QPixmap(32, 32)
        fb.fill(QColor(120, 120, 120))
        _BLOCK_ICON_PM = fb
    else:
        _BLOCK_ICON_PM = pm.scaled(
            32,
            32,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
    return _BLOCK_ICON_PM


def sync_material_list_row_heights(table: QTableWidget, theme_id: str) -> None:
    tid = normalize_theme_id(theme_id)
    rh = content_list_row_height_px(tid)
    vh = table.verticalHeader()
    if rh is None:
        for r in range(table.rowCount()):
            table.resizeRowToContents(r)
    else:
        vh.setDefaultSectionSize(rh)
        for r in range(table.rowCount()):
            table.setRowHeight(r, rh)


def sync_material_list_icon_backgrounds(table: QTableWidget, theme_id: str) -> None:
    """图标列与内容列表一致：Metro / Minecraft 下行选、悬停铺 ``table_list_*`` 底色。"""
    tid = normalize_theme_id(theme_id)
    if not (is_metro_list_table_theme(tid) or tid == "Minecraft"):
        return
    m10 = METRO10_LIST_TABLE_TOKENS
    mc = MINECRAFT_LIST_TABLE_TOKENS
    selected = {idx.row() for idx in table.selectionModel().selectedRows()}
    hr = getattr(table, "_material_hover_row", None)
    for r in range(table.rowCount()):
        w = table.cellWidget(r, 0)
        if w is None:
            continue
        is_sel = r in selected
        is_hov = hr is not None and r == hr and not is_sel
        if is_metro_list_table_theme(tid):
            if is_sel:
                w.setStyleSheet(f"background-color: {m10.selected_bg_hex}; border: none;")
            elif is_hov:
                w.setStyleSheet(f"background-color: {m10.hover_bg_hex}; border: none;")
            else:
                w.setStyleSheet("background-color: transparent; border: none;")
        else:
            if is_sel:
                w.setStyleSheet(f"background-color: {mc.selected_bg_hex}; border: none;")
            elif is_hov:
                w.setStyleSheet(f"background-color: {mc.hover_bg_hex}; border: none;")
            else:
                w.setStyleSheet("background-color: transparent; border: none;")


def refresh_material_list_row_visuals(table: QTableWidget) -> None:
    tid = str(getattr(table, "_material_list_theme_id", "QTDefault"))
    sync_material_list_icon_backgrounds(table, tid)
    table.viewport().update()


class _MaterialListTextColumnsDelegate(QStyledItemDelegate):
    """名称/总计列：Metro8·10 与 Minecraft 与 ``table_list_*`` 一致。"""

    def __init__(self, table: QTableWidget) -> None:
        super().__init__(table)
        self._table = table

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:  # type: ignore[override]
        if index.column() not in (1, 2):
            super().paint(painter, option, index)
            return
        tid = normalize_theme_id(str(getattr(self._table, "_material_list_theme_id", "QTDefault")))
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        row = index.row()
        sel = self._table.selectionModel().isRowSelected(row, QModelIndex())
        hr = getattr(self._table, "_material_hover_row", None)
        text_pen = opt.palette.color(QPalette.ColorRole.Text)

        if is_metro_list_table_theme(tid):
            m10 = METRO10_LIST_TABLE_TOKENS
            painter.save()
            painter.setClipRect(opt.rect)
            if sel:
                painter.fillRect(opt.rect, QColor(m10.selected_bg_hex))
            elif hr is not None and row == hr:
                painter.fillRect(opt.rect, QColor(m10.hover_bg_hex))
            else:
                painter.fillRect(opt.rect, QColor(m10.item_bg_primary_hex))
            painter.setPen(text_pen)
            tr = opt.rect.adjusted(4, 0, -4, 0)
            elided = QFontMetrics(opt.font).elidedText(
                opt.text, Qt.TextElideMode.ElideRight, max(1, tr.width())
            )
            painter.drawText(tr, int(opt.displayAlignment), elided)
            painter.restore()
            return

        if tid == "Minecraft":
            mc = MINECRAFT_LIST_TABLE_TOKENS
            if sel:
                painter.save()
                painter.setClipRect(opt.rect)
                painter.fillRect(opt.rect, QColor(mc.selected_bg_hex))
                painter.setPen(QColor(mc.text_fg_hex))
                tr = opt.rect.adjusted(4, 0, -4, 0)
                elided = QFontMetrics(opt.font).elidedText(
                    opt.text, Qt.TextElideMode.ElideRight, max(1, tr.width())
                )
                painter.drawText(tr, int(opt.displayAlignment), elided)
                painter.restore()
                return
            if hr is not None and row == hr:
                painter.save()
                painter.setClipRect(opt.rect)
                painter.fillRect(opt.rect, QColor(mc.hover_bg_hex))
                painter.setPen(QColor(mc.text_fg_hex))
                tr = opt.rect.adjusted(4, 0, -4, 0)
                elided = QFontMetrics(opt.font).elidedText(
                    opt.text, Qt.TextElideMode.ElideRight, max(1, tr.width())
                )
                painter.drawText(tr, int(opt.displayAlignment), elided)
                painter.restore()
                return
            super().paint(painter, option, index)
            return

        super().paint(painter, option, index)


class _MaterialListHoverFilter(QObject):
    def __init__(self, table: QTableWidget) -> None:
        super().__init__(table)
        self._table = table

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if obj is self._table.viewport():
            tid = normalize_theme_id(str(getattr(self._table, "_material_list_theme_id", "QTDefault")))
            if is_metro_list_table_theme(tid) or tid == "Minecraft":
                if event.type() == QEvent.Type.MouseMove and isinstance(event, QMouseEvent):
                    r = self._table.rowAt(int(event.position().y()))
                    self._set_hover(r if r >= 0 else None)
                elif event.type() == QEvent.Type.Leave:
                    self._set_hover(None)
        return super().eventFilter(obj, event)

    def _set_hover(self, row: int | None) -> None:
        if row == getattr(self._table, "_material_hover_row", None):
            return
        self._table._material_hover_row = row  # type: ignore[attr-defined]
        refresh_material_list_row_visuals(self._table)


def _install_material_list_interaction_once(table: QTableWidget) -> None:
    if getattr(table, "_material_list_interaction_installed", False):
        return
    table._material_list_interaction_installed = True  # type: ignore[attr-defined]
    table._material_hover_row = None  # type: ignore[attr-defined]
    d = _MaterialListTextColumnsDelegate(table)
    table.setItemDelegateForColumn(1, d)
    table.setItemDelegateForColumn(2, d)
    filt = _MaterialListHoverFilter(table)
    table._material_list_hover_filter = filt  # type: ignore[attr-defined]
    table.viewport().installEventFilter(filt)
    table.selectionModel().selectionChanged.connect(lambda *_: refresh_material_list_row_visuals(table))


def configure_material_list_table(table: QTableWidget, theme_id: str) -> None:
    tid = normalize_theme_id(theme_id)
    table._material_list_theme_id = tid  # type: ignore[attr-defined]
    table.setObjectName("MaterialListTable")
    if is_metro_list_table_theme(tid):
        apply_metro_list_flat_chrome_flags(table)
    elif is_minecraft_list_table_theme(tid):
        apply_minecraft_content_list_chrome_flags(table)
    else:
        table.setShowGrid(False)
        table.setAlternatingRowColors(tid != "QTDefault")
        table.setStyleSheet("")
    apply_mcmeta_table_viewport_fill_below_items(table, tid)
    apply_minecraft_list_table_header_chrome(table, tid)
    _install_material_list_interaction_once(table)
    sync_material_list_row_heights(table, tid)
    refresh_material_list_row_visuals(table)
