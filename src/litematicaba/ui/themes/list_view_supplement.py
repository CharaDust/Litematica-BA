"""为版本管理等对话框中的 QTableWidget 追加与各主题一致的 QSS（主主题文件未覆盖 QAbstractItemView）。"""

from __future__ import annotations

from litematicaba.core.settings import DEFAULT_THEME, VALID_THEMES

# 仅作用于带 objectName 的对话框，避免污染其它表格控件。
# 注意：QTableWidget 行高基本不受 QSS 的 ::item min-height 控制，须由对话框内 setDefaultSectionSize/setRowHeight 应用下列数值。
_SEL = "QDialog#McmetaVersionPickerDialog QTableWidget#McmetaVersionTable"

# 与 metro10.py / minecraft.py 中「列表行高」约定一致；仅列出的主题在资源管理表格中强制行高，其余保持 Qt 默认。
MCMETA_TABLE_ROW_HEIGHT_PX_BY_THEME: dict[str, int] = {
    "Metro10": 60,
    "Minecraft": 44,
}


def mcmeta_version_table_list_row_height_px(theme_id: str) -> int | None:
    tid = theme_id if theme_id in VALID_THEMES else DEFAULT_THEME
    return MCMETA_TABLE_ROW_HEIGHT_PX_BY_THEME.get(tid)

# 与各主题控件疏密一致：版本列表区域最小高度（像素），由对话框 setMinimumHeight 使用。
MCMETA_TABLE_MIN_HEIGHT_PX_BY_THEME: dict[str, int] = {
    "QTDefault": 300,
    "Glass7": 320,
    "Metro8": 288,
    "Metro10": 304,
    "Fluent11": 336,
    "LightMac": 312,
    "Bootstrap5": 324,
    "Minecraft": 352,
}


def mcmeta_version_table_min_height_px(theme_id: str) -> int:
    tid = theme_id if theme_id in VALID_THEMES else DEFAULT_THEME
    return MCMETA_TABLE_MIN_HEIGHT_PX_BY_THEME.get(tid, MCMETA_TABLE_MIN_HEIGHT_PX_BY_THEME["QTDefault"])

LIST_VIEW_QSS_BY_THEME: dict[str, str] = {
    "Fluent11": f"""
    {_SEL} {{
      border: 1px solid #d1d1d6;
      border-radius: 6px;
      background-color: #ffffff;
      alternate-background-color: #f5f5f7;
      padding: 4px;
      outline: none;
    }}
    {_SEL}::item:selected {{
      background-color: #0067c0;
      color: #ffffff;
    }}
    """,
    "Glass7": f"""
    {_SEL} {{
      border: 1px solid rgba(80,120,180,0.55);
      border-radius: 4px;
      background-color: rgba(255,255,255,0.75);
      alternate-background-color: rgba(255,255,255,0.55);
      padding: 4px;
      outline: none;
    }}
    {_SEL}::item:selected {{
      background-color: rgba(0,114,198,0.9);
      color: #ffffff;
    }}
    """,
    "Metro8": f"""
    {_SEL} {{
      border: 2px solid #000000;
      border-radius: 0;
      background-color: #ffffff;
      alternate-background-color: #f0f0f0;
      padding: 2px;
      outline: none;
    }}
    {_SEL}::item:selected {{
      background-color: #0078d7;
      color: #ffffff;
    }}
    """,
    "Metro10": f"""
    {_SEL} {{
      border: 1px solid #c8c8c8;
      border-radius: 0;
      background-color: #ffffff;
      padding: 2px;
      outline: none;
    }}
    {_SEL}::item {{
      background-color: transparent;
      border: none;
    }}
    {_SEL}::item:selected {{
      background-color: #0078d4;
      color: #ffffff;
    }}
    """,
    "Bootstrap5": f"""
    {_SEL} {{
      border: 1px solid #ced4da;
      border-radius: 6px;
      background-color: #ffffff;
      alternate-background-color: #f8f9fa;
      padding: 4px;
      outline: none;
    }}
    {_SEL}::item:selected {{
      background-color: #0d6efd;
      color: #ffffff;
    }}
    """,
    "LightMac": f"""
    {_SEL} {{
      border: 1px solid #b4b4b4;
      border-radius: 4px;
      background-color: #ffffff;
      alternate-background-color: #f6f6f6;
      padding: 4px;
      outline: none;
    }}
    {_SEL}::item:selected {{
      background-color: #3d8ce0;
      color: #ffffff;
    }}
    """,
    "Minecraft": f"""
    {_SEL} {{
      border: 2px solid #555555;
      border-radius: 0;
      background-color: #000000;
      color: #ffffff;
      alternate-background-color: #1a1a1a;
      padding: 4px;
      outline: none;
    }}
    {_SEL}::item:selected {{
      background-color: #5a922c;
      color: #ffffff;
    }}
    """,
}


def list_view_supplement_qss(theme_id: str) -> str:
    return LIST_VIEW_QSS_BY_THEME.get(theme_id, "").strip()
