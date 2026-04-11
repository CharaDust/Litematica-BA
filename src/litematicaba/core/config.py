from __future__ import annotations

import sys
from pathlib import Path

_user_accepted_unwritable_data_dir: bool = False


def project_root() -> Path:
    # src/litematicaba/core/config.py -> repository root（源码运行）
    return Path(__file__).resolve().parents[3]


def _user_data_dir_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "data"
    return project_root() / "data"


def set_user_accepted_unwritable_data_dir() -> None:
    """用户已确认在无法写入 data 的环境下继续运行（仅打包场景）。"""
    global _user_accepted_unwritable_data_dir
    _user_accepted_unwritable_data_dir = True


def user_data_dir_is_writable() -> bool:
    """尝试创建 data 目录并写入探测文件；失败表示当前环境无法持久化数据。"""
    path = _user_data_dir_path()
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError:
        return False
    return True


def user_data_dir() -> Path:
    path = _user_data_dir_path()
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        if getattr(sys, "frozen", False) and _user_accepted_unwritable_data_dir:
            pass
        else:
            raise
    return path
