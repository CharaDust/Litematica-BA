"""NBT 查看器（vscode-nbt 同源）资源路径。

分层与更新约定见仓库 ``docs/nbt_viewer_storage.txt``。

- **包内**：UI 壳（``editor.js``、``index.html``、``editor.css``、codicon），随 NBT Viewer 构建更新。
- **用户数据**：``<user_data_dir>/minecraft-assets/nbt-viewer/mcmeta/`` 为游戏资源；选项页或 ``scripts/fetch_nbt_mcmeta_assets.py`` 更新。
- **合并模式（默认）**：包内 UI + 上述 ``mcmeta/`` → ``.cache/nbt_viewer_merged.html``。
"""

from __future__ import annotations

from pathlib import Path

from litematicaba.core.config import user_data_dir


def packaged_nbt_viewer_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / "web" / "nbt-viewer"


def external_nbt_viewer_dir() -> Path:
    return user_data_dir() / "minecraft-assets" / "nbt-viewer"


_MC_META_FILES = ("blocks.js", "assets.js", "uvmapping.js", "atlas.png")


def mcmeta_dir_complete(mcmeta: Path) -> bool:
    return all((mcmeta / name).is_file() for name in _MC_META_FILES)


def code_bundle_complete(root: Path) -> bool:
    return all(
        (root / name).is_file()
        for name in (
            "index.html",
            "editor.js",
            "editor.css",
            "codicon.css",
            "codicon.ttf",
            "lba_nbt_view_preset_bridge.js",
        )
    )


def full_bundle_complete(root: Path) -> bool:
    return code_bundle_complete(root) and mcmeta_dir_complete(root / "mcmeta")


def _file_uri(p: Path) -> str:
    return p.resolve().as_uri()


def write_merged_nbt_launcher(*, code_root: Path, external_mcmeta: Path) -> Path:
    """将合并启动页写入 ``user_data_dir()/.cache/nbt_viewer_merged.html``。"""
    m = external_mcmeta.resolve()
    c = code_root.resolve()
    cache = user_data_dir() / ".cache"
    cache.mkdir(parents=True, exist_ok=True)
    out = cache / "nbt_viewer_merged.html"
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>NBT Viewer（合并：包内 UI + 外部 mcmeta）</title>
  <link href="{_file_uri(c / "codicon.css")}" rel="stylesheet" />
  <link href="{_file_uri(c / "editor.css")}" rel="stylesheet" />
  <style>
    :root {{
      --vscode-descriptionForeground: #9d9d9d;
      --vscode-input-background: #3c3c3c;
      --vscode-input-foreground: #cccccc;
      --vscode-input-border: #3c3c3c;
      --vscode-input-placeholderForeground: #767676;
      --vscode-focusBorder: #007fd4;
      --vscode-selection-background: #264f78;
      --vscode-editor-selectionBackground: #264f78;
      --vscode-editor-background: #1e1e1e;
      --vscode-editor-foreground: #d4d4d4;
      --vscode-sideBar-background: #252526;
      --vscode-sideBar-foreground: #cccccc;
      --vscode-button-background: #0e639c;
      --vscode-button-foreground: #ffffff;
      --vscode-button-hoverBackground: #1177bb;
    }}
    html, body {{
      margin: 0;
      height: 100%;
      overflow: hidden;
      background: var(--vscode-editor-background);
      color: var(--vscode-editor-foreground);
    }}
    .panel-menu {{ flex-shrink: 0; }}
    .find-widget {{ display: none !important; }}
    .nbt-editor {{ flex: 1; min-height: 0; }}
    .file-info {{ display: none; }}
    .texture-atlas {{ display: none; }}
  </style>
</head>
<body>
  <div class="panel-menu"></div>
  <div class="find-widget"></div>
  <div class="nbt-editor"></div>
  <div class="file-info"></div>

  <img class="texture-atlas" src="{_file_uri(m / "atlas.png")}" alt="" />
  <script src="{_file_uri(m / "assets.js")}"></script>
  <script src="{_file_uri(m / "uvmapping.js")}"></script>
  <script src="{_file_uri(m / "blocks.js")}"></script>

  <script>
    function acquireVsCodeApi() {{
      return {{ postMessage: function () {{}} }};
    }}
  </script>
  <script src="{_file_uri(c / "editor.js")}"></script>
  <script src="{_file_uri(c / "lba_nbt_view_preset_bridge.js")}"></script>
</body>
</html>
"""
    out.write_text(html, encoding="utf-8")
    return out


def resolve_nbt_viewer_html_path() -> tuple[Path | None, str]:
    """解析应加载的本地 HTML 路径与模式标签。

    返回 ``(path, mode)``，``mode`` 为 ``external`` | ``merged`` | ``none``。
    包内不再携带 mcmeta；无 ``data/.../mcmeta`` 时返回 ``none``（须先运行 fetch 脚本）。
    """
    ext = external_nbt_viewer_dir()
    pkg = packaged_nbt_viewer_dir()
    ext_mc = ext / "mcmeta"

    if full_bundle_complete(ext):
        return ext / "index.html", "external"
    if code_bundle_complete(pkg) and mcmeta_dir_complete(ext_mc):
        return write_merged_nbt_launcher(code_root=pkg, external_mcmeta=ext_mc), "merged"
    return None, "none"
