"""Minecraft 主题。"""

from __future__ import annotations

from litematicaba.ui.table.minecraft_list_profile import minecraft_theme_table_item_min_height_px
from litematicaba.ui.themes.base import ThemeDef, qss_url, resource_dir


# 控件总高度目标（px）；QSS 的 min/max-height 作用于 **内容区**，不含 border 与 padding
# 10×10 源图：四边各 4px 为九宫格边界（四角 4×4 固定，边条与中心区按 stretch 拉伸，等同 Windows 边框图逻辑）
# 按钮
_BTN_SLICE = 4 # 九宫格边框大小
_BTN_HEIGHT_OUTER = 40 # 按钮高度
_BTN_PAD_VER = 4 # 按钮垂直内边距
_BTN_PAD_HOR = 12 # 按钮水平内边距
# 侧栏
_NAV_OUTER_HEIGHT = 48 # 侧栏内总高
# 输入框
# 单行输入类控件总高（QSS min/max-height 为内容区，不含 border 与 padding）
_INPUT_OUTER_HEIGHT = 44 # 输入框高度
_INPUT_BORDER_PX = 2 # 输入框边框大小
_INPUT_PAD_V = 4 # 输入框垂直内边距
_INPUT_PAD_H = 8 # 输入框水平内边距
def build_qss() -> str:
    # 资源路径
    UI_mc_dir = resource_dir("minecraft")
    # 按钮
    button_mc_normal = qss_url(UI_mc_dir / "button_normal_min.png")
    button_mc_hover = qss_url(UI_mc_dir / "button_hover_min.png")
    button_mc_checked = qss_url(UI_mc_dir / "button_check_min.png")
    button_mc_disabled = qss_url(UI_mc_dir / "button_disabled_min.png")
    # 单选框
    radio_mc_default = qss_url(UI_mc_dir / "radio_default.png")
    radio_mc_hover = qss_url(UI_mc_dir / "radio_hover.png")
    radio_mc_checked = qss_url(UI_mc_dir / "radio_checked.png")
    radio_mc_checked_hover = qss_url(UI_mc_dir / "radio_checked_hover.png")
    # 复选框
    checkbox_mc_default = qss_url(UI_mc_dir / "checkbox_default.png")
    checkbox_mc_hover = qss_url(UI_mc_dir / "checkbox_hover.png")
    checkbox_mc_checked = qss_url(UI_mc_dir / "checkbox_checked.png")
    checkbox_mc_checked_hover = qss_url(UI_mc_dir / "checkbox_checked_hover.png")
    # 箭头
    arrow_mc_up = qss_url(UI_mc_dir / "arrow_up.png")
    arrow_mc_down = qss_url(UI_mc_dir / "arrow_down.png")
    arrow_mc_left = qss_url(UI_mc_dir / "arrow_left.png")
    arrow_mc_right = qss_url(UI_mc_dir / "arrow_right.png")
    spin_mc_plus = qss_url(UI_mc_dir / "spin_plus.png")
    spin_mc_minus = qss_url(UI_mc_dir / "spin_minus.png")
    # 九宫格样式
    button_mc_9Grid_cornerSize = _BTN_SLICE
    # 按钮尺寸
    #>总高 ≈ 内容区 min-height + 上下 padding + 上下 border（与 Qt 盒模型一致）
    button_padding_mc_ver = _BTN_PAD_VER
    button_padding_mc_hor = _BTN_PAD_HOR
    button_border_mc_ver = button_mc_9Grid_cornerSize
    button_height_mc_content = _BTN_HEIGHT_OUTER - button_border_mc_ver - ( 2* button_padding_mc_ver ) 
    
    # 侧栏
    nav_height_mc_content = _NAV_OUTER_HEIGHT - ( 2 * button_border_mc_ver ) - ( 2 * button_padding_mc_ver )
    # 输入框
    ib = _INPUT_BORDER_PX
    ib_v = 2 * ib
    ip_v = 2 * _INPUT_PAD_V
    h_input_content = _INPUT_OUTER_HEIGHT - ib_v - ip_v
    ipv = _INPUT_PAD_V
    iph = _INPUT_PAD_H
    list_item_row_h = minecraft_theme_table_item_min_height_px()
    # 颜色
    color_background_mc_window = "#3c3c3c" # 主界面背景
    color_text_mc = "#c6c6c6" # 主界面文字

    # 生成九宫格样式按钮
    def button_mc_gen(url: str) -> str:
        return (
            f'border-width: {button_mc_9Grid_cornerSize}px; border-style: solid; border-color: transparent; '
            f'border-image: url("{url}") {button_mc_9Grid_cornerSize} {button_mc_9Grid_cornerSize} {button_mc_9Grid_cornerSize} {button_mc_9Grid_cornerSize} stretch stretch;'
        )

    return f"""
    /* 主界面基础样式 */
    QWidget {{
        background-color: {color_background_mc_window};
        color: {color_text_mc};
        font-size: 12pt;
        font-family: "Unifont", "GNU Unifont", "Courier New", monospace;
    }}
    /* 纯文字控件 */
    QLabel,
    /* 复选框 */
    QCheckBox,
    /* 单选框 */
    QRadioButton {{
        background-color: transparent;
    }}
    /* 主窗口 */
    QMainWindow {{ background-color: {color_background_mc_window}; }}
    /* 滚动区域 */
    QScrollArea {{ 
        border: 2px solid #555555; 
        background-color: #2b2b2b; 
    }}
    /* 分组框 */
    QGroupBox {{
        font-weight: bold;
        border: 2px solid #555555;
        border-radius: 0;
        margin-top: 10px;
        padding-top: 8px;
        background-color: #2b2b2b;
    }}
    /* 分组框标题 */
    QGroupBox::title {{ 
        font-weight: bold;
        subcontrol-origin: margin; 
        left: 8px; 
        padding: 0 4px; }}

    /* 列表 */
    QListWidget::item,
    QTreeView::item,
    QTableView::item {{
        min-height: {list_item_row_h}px;
    }}

    QComboBox QListView::item {{
        min-height: 24px;
    }}

    /* 按钮 */
    QPushButton, 
    /* 工具按钮 */
    QToolButton {{
        background-color: transparent;
        border-radius: 0;
        padding: {button_padding_mc_ver}px {button_padding_mc_hor}px;
        min-height: {button_height_mc_content}px;
        max-height: {button_height_mc_content}px;
        color: #ffffff;
        {button_mc_gen(button_mc_normal)}
    }}
    /* ：默认态 */
    QPushButton:default, QToolButton:default {{
        color: #ffff00;
        {button_mc_gen(button_mc_normal)}
    }}
    /* ：悬停态 */
    QPushButton:hover:enabled, QToolButton:hover:enabled {{
        color: #ffff00;
        {button_mc_gen(button_mc_hover)}
    }}
    /* ：按下态 */
    QPushButton:pressed, QToolButton:pressed {{
        color: #ffff00;
        {button_mc_gen(button_mc_normal)}
    }}
    /* ：选中态 */
    QPushButton:checked, QToolButton:checked {{
        color: #ffff00;
        {button_mc_gen(button_mc_checked)}
    }}
    /* ：选中态&&悬停态 */
    QPushButton:checked:hover:enabled, QToolButton:checked:hover:enabled {{
        color: #ffff00;
        {button_mc_gen(button_mc_checked)}
    }}
    /* ：选中态&&按下态 */
    QPushButton:checked:pressed, QToolButton:checked:pressed {{
        color: #ffff00;
        {button_mc_gen(button_mc_normal)}
    }}
    /* ：禁用态 */
    QPushButton:disabled, QToolButton:disabled {{
        color: #808080;
        {button_mc_gen(button_mc_disabled)}
    }}
    /* ：选中态&&禁用态 */
    QPushButton:checked:disabled, QToolButton:checked:disabled {{
        color: #808080;
        {button_mc_gen(button_mc_disabled)}
    }}

    /* 侧栏 */
    #navSidebar QPushButton#navExpand,
    #navSidebar QPushButton#navItem {{
        min-height: {nav_height_mc_content}px;
        max-height: {nav_height_mc_content}px;
    }}

    /* 输入框 */
    QLineEdit, QComboBox {{
        border: {ib}px solid #a0a0a0;
        border-radius: 0;
        padding: {ipv}px {iph}px;
        background-color: #000000;
        color: #ffffff;
        min-height: {h_input_content}px;
        max-height: {h_input_content}px;
    }}
    QLineEdit:focus, QComboBox:focus {{
        border: {ib}px solid #ffffff;
    }}
    QLineEdit:focus:hover, QComboBox:focus:hover {{
        border: {ib}px solid #ffffff;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
        background-color: #000000;
    }}

    QAbstractSpinBox {{
        border: {ib}px solid #a0a0a0;
        border-radius: 0;
        padding: {ipv}px {iph}px;
        padding-right: 28px;
        background-color: #000000;
        color: #ffffff;
        min-height: {h_input_content}px;
        max-height: {h_input_content}px;
    }}
    QAbstractSpinBox:focus {{
        border: {ib}px solid #ffffff;
    }}
    QAbstractSpinBox:focus:hover {{
        border: {ib}px solid #ffffff;
    }}
    QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
        subcontrol-origin: border;
        background-color: #000000;
        border: none;
        width: 14px;
    }}
    QAbstractSpinBox::up-button:hover:enabled, QAbstractSpinBox::down-button:hover:enabled {{
        background-color: #2a2a2a;
    }}

    QRadioButton::indicator {{
        width: 20px; height: 20px;
        border: none;
        background: transparent;
        image: url("{radio_mc_default}");
    }}
    QRadioButton::indicator:hover:enabled {{ image: url("{radio_mc_hover}"); }}
    QRadioButton::indicator:checked {{ image: url("{radio_mc_checked}"); }}
    QRadioButton::indicator:checked:hover:enabled {{ image: url("{radio_mc_checked_hover}"); }}
    QCheckBox::indicator {{
        width: 20px; height: 20px;
        border: none;
        background-color: transparent;
        image: url("{checkbox_mc_default}");
    }}
    QCheckBox::indicator:hover:enabled {{ image: url("{checkbox_mc_hover}"); }}
    QCheckBox::indicator:checked {{ image: url("{checkbox_mc_checked}"); }}
    QCheckBox::indicator:checked:hover:enabled {{ image: url("{checkbox_mc_checked_hover}"); }}

    QSlider::groove:horizontal {{ height: 8px; background: #555555; border-radius: 0; }}
    QSlider::handle:horizontal {{
        width: 12px; height: 18px; margin: -5px 0;
        background: #737373; border: 2px solid #000000; border-radius: 0;
    }}
    QFrame[frameShape="4"] {{ color: #555555; max-height: 2px; }}
    """


THEME_MINECRAFT = ThemeDef(theme_id="Minecraft", build_qss=build_qss, widget_support={"tile"})
