from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    # src/litematicaba/core/config.py -> repository root
    return Path(__file__).resolve().parents[3]


def user_data_dir() -> Path:
    path = project_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path
