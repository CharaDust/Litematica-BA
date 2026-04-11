"""应用选项持久化（JSON）。

源码运行：``<仓库>/data/settings.json``。
打包后：``<exe 所在目录>/data/settings.json``。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from litematicaba.core.config import user_data_dir

VALID_THEMES = (
    "QTDefault",
    "Glass7",
    "Metro8",
    "Metro10",
    "Fluent11",
    "LightMac",
    "Bootstrap5",
    "Minecraft",
)
DEFAULT_THEME = "QTDefault"


@dataclass
class AppSettings:
    display_name: str = "User"
    slogan_visible: bool = True
    slogan_text: str = "今天也随便看看吧"
    slogan_pt: int = 24
    theme_id: str = DEFAULT_THEME
    show_ui_test_nav: bool = True
    show_tile_grid: bool = False
    tile_auto_place_preferred_cols: int = 12
    tile_view_right_padding_px: int = 64
    show_widget_inspector: bool = False
    pick_common_groups: list[dict[str, str]] = field(default_factory=list)

    def normalized(self) -> AppSettings:
        t = self.theme_id if self.theme_id in VALID_THEMES else DEFAULT_THEME
        pt = max(18, min(36, int(self.slogan_pt)))
        groups: list[dict[str, str]] = []
        for item in self.pick_common_groups:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            path = str(item.get("path", "")).strip()
            if not name or not path:
                continue
            groups.append({"name": name, "path": path})
        return AppSettings(
            display_name=self.display_name.strip() or "User",
            slogan_visible=self.slogan_visible,
            slogan_text=self.slogan_text or "今天也随便看看吧",
            slogan_pt=pt,
            theme_id=t,
            show_ui_test_nav=self.show_ui_test_nav,
            show_tile_grid=bool(self.show_tile_grid),
            tile_auto_place_preferred_cols=max(1, min(64, int(self.tile_auto_place_preferred_cols))),
            tile_view_right_padding_px=max(0, min(300, int(self.tile_view_right_padding_px))),
            show_widget_inspector=bool(self.show_widget_inspector),
            pick_common_groups=groups,
        )


def _settings_path() -> Path:
    return user_data_dir() / "settings.json"


def load_settings() -> AppSettings:
    path = _settings_path()
    if not path.is_file():
        return AppSettings()
    try:
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppSettings()
    return AppSettings(
        display_name=str(raw.get("display_name", "User")),
        slogan_visible=bool(raw.get("slogan_visible", True)),
        slogan_text=str(raw.get("slogan_text", "今天也随便看看吧")),
        slogan_pt=int(raw.get("slogan_pt", 24)),
        theme_id=str(raw.get("theme_id", DEFAULT_THEME)),
        show_ui_test_nav=bool(raw.get("show_ui_test_nav", True)),
        show_tile_grid=bool(raw.get("show_tile_grid", False)),
        tile_auto_place_preferred_cols=int(raw.get("tile_auto_place_preferred_cols", 9)),
        tile_view_right_padding_px=int(raw.get("tile_view_right_padding_px", 64)),
        show_widget_inspector=bool(raw.get("show_widget_inspector", False)),
        pick_common_groups=list(raw.get("pick_common_groups", [])),
    ).normalized()


def save_settings(settings: AppSettings) -> None:
    path = _settings_path()
    data = asdict(settings.normalized())
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
