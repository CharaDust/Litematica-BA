"""为版本选择等对话框中的 QListWidget 追加与各主题一致的 QSS（主主题文件未覆盖 QAbstractItemView）。"""

from __future__ import annotations

# 仅作用于带 objectName 的对话框，避免污染其它列表控件。
_SEL = "QDialog#McmetaVersionPickerDialog QListWidget#McmetaVersionPickerList"

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
    {_SEL}::item:hover:!selected {{
      background-color: #f0f6fc;
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
    {_SEL}::item:hover:!selected {{
      background-color: rgba(255,255,255,0.9);
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
    {_SEL}::item:hover:!selected {{
      background-color: #e5f3ff;
    }}
    """,
    "Metro10": f"""
    {_SEL} {{
      border: 1px solid #c8c8c8;
      border-radius: 0;
      background-color: #ffffff;
      alternate-background-color: #f5f5f5;
      padding: 2px;
      outline: none;
    }}
    {_SEL}::item:selected {{
      background-color: #0078d4;
      color: #ffffff;
    }}
    {_SEL}::item:hover:!selected {{
      background-color: #e5f1fb;
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
    {_SEL}::item:hover:!selected {{
      background-color: #e7f1ff;
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
    {_SEL}::item:hover:!selected {{
      background-color: #eaf3fc;
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
    {_SEL}::item:hover:!selected {{
      background-color: #3c3c3c;
    }}
    """,
}


def list_view_supplement_qss(theme_id: str) -> str:
    return LIST_VIEW_QSS_BY_THEME.get(theme_id, "").strip()
