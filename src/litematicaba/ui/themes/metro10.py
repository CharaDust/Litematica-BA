from __future__ import annotations

from litematicaba.ui.themes.base import ThemeDef, qss_url, resource_dir
from litematicaba.ui.themes.sidebar_nav_win10 import NAV_SIDEBAR_WIN10_QSS

# 按钮
_BTN_HEIGHT_OUTER = 31 # 按钮高度
_BTN_BRD_WIDTH = 2 # 按钮边框宽度
_BTN_PAD_VER = 0 # 按钮垂直内边距
_BTN_PAD_HOR = 12 # 按钮水平内边距

def build_qss() -> str:
    # 资源路径
    UI_M10_dir = resource_dir("metro10")
    # 单选框
    radio_M10_default = qss_url(UI_M10_dir / "radio_default.svg")
    radio_M10_hover = qss_url(UI_M10_dir / "radio_hover.svg")
    radio_M10_checked = qss_url(UI_M10_dir / "radio_checked.svg")
    radio_M10_checked_hover = qss_url(UI_M10_dir / "radio_checked_hover.svg")
    # 复选框
    checkbox_M10_default = qss_url(UI_M10_dir / "checkbox_default.svg")
    checkbox_M10_hover = qss_url(UI_M10_dir / "checkbox_hover.svg")
    checkbox_M10_checked = qss_url(UI_M10_dir / "checkbox_checked.svg")
    checkbox_M10_checked_hover = qss_url(UI_M10_dir / "checkbox_checked_hover.svg")
    # 滑块
    slider_M10_handle = qss_url(UI_M10_dir / "slider_handle.svg")
    # 箭头
    arrow_M10_up = qss_url(UI_M10_dir / "arrow_up.svg")
    arrowv_M10_down = qss_url(UI_M10_dir / "arrow_down.svg")
    arrow_M10_left = qss_url(UI_M10_dir / "arrow_left.svg")
    arrow_M10_right = qss_url(UI_M10_dir / "arrow_right.svg")
    spin_M10_plus = qss_url(UI_M10_dir / "spin_plus.svg")
    spin_M10_minus = qss_url(UI_M10_dir / "spin_minus.svg")
    # 颜色
    color_background_M10_window = "#ffffff" # 主界面背景
    color_text_M10 = "#1a1a1a" # 主界面文字

    return (
        NAV_SIDEBAR_WIN10_QSS
        + """
    /* 主界面基础样式 */
    QWidget { 
        background-color: {color_background_M10_window}; 
        color: {color_text_M10}; 
        font-size: 10pt; 
    }
    /* 纯文字控件 */
    QLabel,
    /* 复选框 */
    QCheckBox,
    /* 单选框 */
    QRadioButton {
        background-color: transparent;
    }
    /* 主窗口 */
    QMainWindow { background-color: {color_background_M10_window}; }
    /* 滚动区域 */
    QScrollArea { 
        border: none; 
        background-color: transparent; 
    }
    /* 分组框 */
    QGroupBox {
        font-weight: regular;
        font-size: 18pt;
        border: 1px solid #c8c8c8;
        border-radius: 0;
        margin-top: 10px;
        padding-top: 18px;
        background-color: #fafafa;
    }
    /* 分组框标题 */
    QGroupBox::title { 
        font-size: 18pt;
        subcontrol-origin: margin; 
        left: 10px; 
        padding: 0 4px; 
    }

    /* 列表默认行高约定：60px；QComboBox 下拉项：32px */
    QListWidget::item,
    QTreeView::item,
    QTableView::item {
        min-height: 60px;
    }
    QComboBox QListView::item {
        min-height: 32px;
    }

    /* 按钮 */
    QPushButton, 
    /* 工具按钮 */
    QToolButton {
        background-color: #cccccc;
        border: 2px solid transparent;
        border-radius: 0px;
        padding: 0px 12px;
        min-height: 27px;
        max-height: 27px;
    }
    /* ：悬停态 */
    QPushButton:hover:enabled, QToolButton:hover:enabled {
        border-color: #7a7a7a;
    }
    /* ：按下态 */
    QPushButton:pressed, QToolButton:pressed { background-color: #999999; }
    /* ：选中态 */
    QPushButton:checked, QToolButton:checked {
        background-color: #999999;
    }
    /* ：禁用态 */
    QPushButton:disabled, QToolButton:disabled {
        color: #7a7a7a;
    }

    /* 输入框 */
    QLineEdit, QComboBox {
        border: 2px solid #999999;
        border-radius: 0px;
        padding: 3px 8px;
        background-color: #ffffff;
        min-height: 22px;
    }
    QLineEdit:hover:enabled, QComboBox:hover:enabled { border-color: #666666; }
    QLineEdit:focus { border-color: #0078d7; }
    QLineEdit:focus:hover { border-color: #0078d7; }
    QComboBox::drop-down { border: none; width: 24px; }

    QAbstractSpinBox {
        border: 2px solid #999999;
        border-radius: 0px;
        padding: 0px 60px 0px 8px;
        background-color: #ffffff;
        min-height: 28px;
        max-height: 28px;
    }
    QAbstractSpinBox:hover:enabled { border-color: #666666; }
    QAbstractSpinBox:focus { border-color: #0078d7; }
    QAbstractSpinBox:focus:hover { border-color: #0078d7; }
    QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
        subcontrol-origin: border;
        background: transparent;
        border: none;
        width: 28px;
        height: 28px;
    }
    QAbstractSpinBox::up-button:hover:enabled, QAbstractSpinBox::down-button:hover:enabled { background: #e9e9e9; }
    QAbstractSpinBox::up-button:pressed, QAbstractSpinBox::down-button:pressed { background: #d9d9d9; }
    QAbstractSpinBox::up-button { subcontrol-position: right; right: 2px; }
    QAbstractSpinBox::down-button { subcontrol-position: right; left: -28px; right: 2px; }
    QAbstractSpinBox::up-arrow, QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
        image: url("%s");
        width: 16px;
        height: 16px;
    }
    QAbstractSpinBox::down-arrow, QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
        image: url("%s");
        width: 16px;
        height: 16px;
    }

    QRadioButton::indicator {
        width: 20px; height: 20px;
        border: none;
        background: transparent;
        image: url("%s");
    }
    QRadioButton::indicator:hover:enabled { image: url("%s"); }
    QRadioButton::indicator:checked { image: url("%s"); }
    QRadioButton::indicator:checked:hover:enabled { image: url("%s"); }
    QCheckBox::indicator {
        width: 20px; height: 20px;
        border: none;
        background-color: transparent;
        image: url("%s");
    }
    QCheckBox::indicator:hover:enabled { image: url("%s"); }
    QCheckBox::indicator:checked { image: url("%s"); }
    QCheckBox::indicator:checked:hover:enabled { image: url("%s"); }

    QSlider:horizontal { min-height: 24px; }
    QSlider::groove:horizontal { height: 2px; margin: 11px 0; background: transparent; border-radius: 1px; }
    QSlider::sub-page:horizontal { height: 2px; margin: 11px 0; background: #0078d7; border-radius: 1px; }
    QSlider::add-page:horizontal { height: 2px; margin: 11px 0; background: #999999; border-radius: 1px; }
    QSlider::handle:horizontal {
        width: 8px; height: 24px; margin: -10px 0;
        background: transparent;
        border: none;
        image: url("%s");
    }

    QScrollBar:vertical {
        background: #e9e9e9;
        width: 16px;
        margin: 16px 0 16px 0;
        border: none;
    }
    QScrollBar::handle:vertical {
        background: #bababa;
        min-height: 20px;
        border: none;
    }
    QScrollBar::handle:vertical:hover { background: #8c8c8c; }
    QScrollBar::handle:vertical:pressed { background: #5d5d5d; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
    QScrollBar::sub-line:vertical {
        background: #e9e9e9;
        height: 16px;
        subcontrol-position: top;
        subcontrol-origin: margin;
        border: none;
    }
    QScrollBar::add-line:vertical {
        background: #e9e9e9;
        height: 16px;
        subcontrol-position: bottom;
        subcontrol-origin: margin;
        border: none;
    }
    QScrollBar::up-arrow:vertical { image: url("%s"); width: 16px; height: 16px; }
    QScrollBar::down-arrow:vertical { image: url("%s"); width: 16px; height: 16px; }

    QScrollBar:horizontal {
        background: #e9e9e9;
        height: 16px;
        margin: 0 16px 0 16px;
        border: none;
    }
    QScrollBar::handle:horizontal {
        background: #bababa;
        min-width: 20px;
        border: none;
    }
    QScrollBar::handle:horizontal:hover { background: #8c8c8c; }
    QScrollBar::handle:horizontal:pressed { background: #5d5d5d; }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
    QScrollBar::sub-line:horizontal {
        background: #e9e9e9;
        width: 16px;
        subcontrol-position: left;
        subcontrol-origin: margin;
        border: none;
    }
    QScrollBar::add-line:horizontal {
        background: #e9e9e9;
        width: 16px;
        subcontrol-position: right;
        subcontrol-origin: margin;
        border: none;
    }
    QScrollBar::left-arrow:horizontal { image: url("%s"); width: 16px; height: 16px; }
    QScrollBar::right-arrow:horizontal { image: url("%s"); width: 16px; height: 16px; }
    """
        % (
            spin_M10_plus,
            spin_M10_minus,
            radio_M10_default,
            radio_M10_hover,
            radio_M10_checked,
            radio_M10_checked_hover,
            checkbox_M10_default,
            checkbox_M10_hover,
            checkbox_M10_checked,
            checkbox_M10_checked_hover,
            slider_M10_handle,
            arrow_M10_up,
            arrowv_M10_down,
            arrow_M10_left,
            arrow_M10_right,
        )
    )


THEME_METRO10 = ThemeDef(theme_id="Metro10", build_qss=build_qss)
