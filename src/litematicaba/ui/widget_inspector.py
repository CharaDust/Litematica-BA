"""鼠标悬停时高亮控件并显示 objectName / 类型 / 尺寸（调试用，不拦截点击）。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

# 判断控件是否包含全局位置
def _host_contains_global(host: QWidget, global_pos: QPoint) -> bool:
    # 获取控件的左上角全局位置
    tl = host.mapToGlobal(QPoint(0, 0))
    # 判断全局位置是否在控件的矩形范围内并返回
    return QRect(tl, host.size()).contains(global_pos)

# 判断控件是否是另一个控件的子控件，如果是返回True，否则返回False
def _is_descendant_of(widget: QWidget, ancestor: QWidget) -> bool:
    # 获取控件的父控件
    w: QWidget | None = widget
    # 循环判断控件是否是另一个控件的子控件
    while w is not None:
        if w is ancestor:
            return True
        w = w.parentWidget()
    return False

# 控件信息内容
def _describe_widget(w: QWidget) -> list[str]:
    # 控件类
    cls = w.metaObject().className()
    # 控件名称
    oid = w.objectName()
    if oid:
        title = f"{cls}  ({oid})"
        id_line = f"objectName: {oid}"
    else:
        title = cls
        id_line = "objectName: (未设置)"
    # 控件尺寸
    size_line = f"尺寸: {w.width()} × {w.height()} px"
    return [title, id_line, size_line]

# 控件信息覆盖层
class WidgetInspectorOverlay(QWidget):
    """覆盖整个主窗口客户端区域；仅绘制高亮与标签，鼠标事件穿透。"""

    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        # 矩形区域
        self._rect = QRect()
        # 控件信息内容
        self._lines: list[str] = []
        # 设置透明鼠标事件穿透
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        # 设置透明背景
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # 设置焦点策略为无焦点（不会被键盘聚焦）
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    # 设置高亮区域（洋红色半透明矩形）和内容
    def set_highlight(self, rect_in_host: QRect, lines: list[str]) -> None:
        # 设置矩形区域
        self._rect = rect_in_host
        # 设置控件信息内容
        self._lines = lines
        # 更新显示
        self.update()

    # 清除残留高亮区域和内容
    def clear_highlight(self) -> None:
        # 设置矩形区域为无效区域
        self._rect = QRect()
        self._lines = []
        self.update()

    # 绘制事件
    def paintEvent(self, event) -> None:  # noqa: ARG002
        # 如果矩形区域无效或为空，则不绘制
        if not self._rect.isValid() or self._rect.isEmpty():
            return
        p = QPainter(self)

        # 设定：抗锯齿渲染
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 设定：高亮区域内部填充颜色样式
        fill = QColor("#ff00ff") # 颜色： 洋红色
        fill.setAlpha(110) # 透明度： 110
        ## 行动：填充高亮区域内部
        p.fillRect(self._rect, fill)

        # 设定：高亮区域边框颜色样式（洋红色）
        pen = QPen(QColor("#ff00ff")) # 颜色： 洋红色
        pen.setWidth(1) # 宽度： 1
        ## 行动：绘制高亮区域边框
        p.setPen(pen)
        p.drawRect(self._rect.adjusted(0, 0, -1, -1))

        # 判断：如果控件信息文本为空，则不绘制
        if not self._lines:
            return
        # 行动：将控件信息内容拼接成字符串
        text = "\n".join(self._lines)
        # 设定：文本字体
        p.setFont(self.font())
        # 行动：获取字体测量对象
        fm = p.fontMetrics()
        # 设定：边距
        margin = 6 # 标签
        pad = 4 # 文本
        # 计算：标签最大宽度
        max_w = max(220, self._rect.width() - margin * 2)
        # 行动：获取文本矩形（文本框）
        text_rect = fm.boundingRect(
            QRect(0, 0, max_w, 5000),
            # 对齐方式：左对齐，换行：按单词换行
            int(Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
            text,
        )
        
        # 计算：标签尺寸
        label_w = min(text_rect.width() + pad * 2, self.width() - margin * 2)
        label_h = text_rect.height() + pad * 2
        # 计算：标签左上角位置
        lx = self._rect.left() + margin
        ly = self._rect.top() + margin
        # 计算：如果标签超出边界，则调整标签位置至边缘
        if ly + label_h > self.height() - margin:
            ly = max(margin, self._rect.top() - label_h - margin)
        if lx + label_w > self.width() - margin:
            lx = max(margin, self.width() - margin - label_w)

        # 行动：创建标签矩形
        label = QRect(lx, ly, label_w, label_h)
        # 设定：标签背景颜色样式（黑色半透明）
        bg = QColor(0, 0, 0, 200)
        ## 行动：填充标签背景
        p.fillRect(label, bg)

        ## 设定：文本颜色样式（白色）
        p.setPen(QColor(255, 255, 255))
        ## 行动：绘制文本
        p.drawText(
            label.adjusted(pad, pad, -pad, -pad),
            int(Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
            text,
        )


class WidgetInspectorController:
    """由主窗口持有：按设置启停定时器并刷新覆盖层。"""

    def __init__(self, host: QWidget) -> None:
        self._host = host
        self._overlay = WidgetInspectorOverlay(host)
        self._overlay.hide()
        self._timer = QTimer(host)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self._enabled = False
    
    # 设置启用状态
    def set_enabled(self, on: bool) -> None:
        if on == self._enabled:
            return
        self._enabled = on
        if on:
            self._sync_geometry()
            self._overlay.show()
            self._overlay.raise_()
            self._timer.start()
        else:
            self._timer.stop()
            self._overlay.clear_highlight()
            self._overlay.hide()

    # 同步几何尺寸
    def sync_geometry(self) -> None:
        if self._enabled:
            self._sync_geometry()

    # 提升覆盖层到顶部
    def raise_overlay(self) -> None:
        if self._enabled:
            self._overlay.raise_()

    # 同步几何尺寸
    def _sync_geometry(self) -> None:
        self._overlay.setGeometry(self._host.rect())

    # 定时器回调，用于更新覆盖层
    def _tick(self) -> None:
        # 判断：如果功能未启用，结束函数
        if not self._enabled:
            return
        # 行动：提升覆盖层到顶部
        self._overlay.raise_()
        # 行动：获取应用程序实例
        app = QApplication.instance()
        # 判断：如果应用程序实例为空，结束函数
        if app is None:
            return
        
        # 行动：获取鼠标位置
        gp = QCursor.pos()
        # 判断：如果鼠标位置不在主机内，清除高亮
        if not _host_contains_global(self._host, gp):
            self._overlay.clear_highlight()
            return
        # 行动：获取鼠标位置的控件
        w = app.widgetAt(gp)
        # 判断：如果控件为空或为覆盖层，清除高亮
        if w is None or w is self._overlay:
            self._overlay.clear_highlight()
            return
        # 判断：如果控件不是主机的子控件，清除高亮
        if not _is_descendant_of(w, self._host):
            self._overlay.clear_highlight()
            return
        # 判断：如果控件不可见，清除高亮
        if not w.isVisible():
            self._overlay.clear_highlight()
            return
        
        # 行动：获取控件信息内容
        lines = _describe_widget(w)
        # 行动：获取控件全局位置
        tl_g = w.mapToGlobal(QPoint(0, 0))
        # 行动：获取控件主机位置
        tl_h = self._host.mapFromGlobal(tl_g)
        # 计算：控件主机矩形区域
        rect = QRect(tl_h, w.size())
        # 行动：设置高亮区域和内容
        self._overlay.set_highlight(rect, lines)
