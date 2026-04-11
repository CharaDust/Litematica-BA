"""应用选项持久化（JSON）。

源码运行：``<仓库>/data/settings.json``。
打包后：``<exe 所在目录>/data/settings.json``。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
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
    theme_id: str = DEFAULT_THEME
    show_ui_test_nav: bool = True
    show_tile_grid: bool = False
    tile_auto_place_preferred_cols: int = 12
    tile_view_right_padding_px: int = 64
    show_widget_inspector: bool = False

    def normalized(self) -> AppSettings:
        t = self.theme_id if self.theme_id in VALID_THEMES else DEFAULT_THEME
        return AppSettings(
            theme_id=t,
            show_ui_test_nav=self.show_ui_test_nav,
            show_tile_grid=bool(self.show_tile_grid),
            tile_auto_place_preferred_cols=max(1, min(64, int(self.tile_auto_place_preferred_cols))),
            tile_view_right_padding_px=max(0, min(300, int(self.tile_view_right_padding_px))),
            show_widget_inspector=bool(self.show_widget_inspector),
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
        theme_id=str(raw.get("theme_id", DEFAULT_THEME)),
        show_ui_test_nav=bool(raw.get("show_ui_test_nav", True)),
        show_tile_grid=bool(raw.get("show_tile_grid", False)),
        tile_auto_place_preferred_cols=int(raw.get("tile_auto_place_preferred_cols", 9)),
        tile_view_right_padding_px=int(raw.get("tile_view_right_padding_px", 64)),
        show_widget_inspector=bool(raw.get("show_widget_inspector", False)),
    ).normalized()


def save_settings(settings: AppSettings) -> None:
    path = _settings_path()
    data = asdict(settings.normalized())
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
