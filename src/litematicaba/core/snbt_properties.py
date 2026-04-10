"""Litematic 属性区（Metadata）读写。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

def _to_int(value, default: int = 0) -> int:
    try:
        if hasattr(value, "py_int"):
            return int(value.py_int)
        return int(str(value))
    except Exception:
        return default


def _to_str(value, default: str = "") -> str:
    if value is None:
        return default
    if hasattr(value, "py_str"):
        try:
            return str(value.py_str)
        except Exception:
            pass
    text = str(value)
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    return text


def _to_int32_signed(value: int) -> int:
    """Normalize Python int to signed int32 range."""
    v = int(value) & 0xFFFFFFFF
    if v >= 0x80000000:
        v -= 0x100000000
    return v


@dataclass(slots=True)
class SnbtProperties:
    file_path: Path | None = None
    file_name: str = ""
    author: str = ""
    description: str = ""
    created_unix: int = 0
    modified_unix: int = 0
    enclosing_size: tuple[int, int, int] = (0, 0, 0)
    total_blocks: int = 0
    total_volume: int = 0
    litematic_version: int = 0
    minecraft_data_version: int = 0
    preview_image_data: list[int] = field(default_factory=list)


def _import_amulet_nbt():
    try:
        from amulet_nbt import IntArrayTag, IntTag, LongTag, NamedTag, StringTag, load
    except Exception as exc:
        raise RuntimeError(
            "缺少依赖 amulet_nbt，请先安装 requirements.txt 后再使用 SNBT 读写。"
        ) from exc
    return IntArrayTag, IntTag, LongTag, NamedTag, StringTag, load


def load_snbt_properties(file_path: str | Path) -> SnbtProperties:
    _, _, _, NamedTag, _, load = _import_amulet_nbt()
    path = Path(file_path)
    nbt: NamedTag = load(str(path), compressed=True)
    root = nbt.tag
    metadata = root.get("Metadata", {})
    enclosing = metadata.get("EnclosingSize", {})

    preview_tag = metadata.get("PreviewImageData")
    preview_data: list[int] = []
    if preview_tag is not None:
        try:
            preview_data = [int(v) for v in preview_tag]
        except Exception:
            preview_data = []

    mc_data_ver = _to_int(metadata.get("MinecraftDataVersion"), 0)
    if mc_data_ver == 0:
        mc_data_ver = _to_int(root.get("MinecraftDataVersion"), 0)

    props = SnbtProperties(
        file_path=path,
        file_name=path.name,
        author=_to_str(metadata.get("Author"), ""),
        description=_to_str(metadata.get("Description"), ""),
        created_unix=_to_int(metadata.get("TimeCreated"), 0),
        modified_unix=_to_int(metadata.get("TimeModified"), 0),
        enclosing_size=(
            _to_int(enclosing.get("x"), 0),
            _to_int(enclosing.get("y"), 0),
            _to_int(enclosing.get("z"), 0),
        ),
        total_blocks=_to_int(metadata.get("TotalBlocks"), 0),
        total_volume=_to_int(metadata.get("TotalVolume"), 0),
        litematic_version=_to_int(root.get("Version"), 0),
        minecraft_data_version=mc_data_ver,
        preview_image_data=preview_data,
    )
    return props


def save_snbt_properties(data: SnbtProperties, output_path: str | Path | None = None) -> Path:
    IntArrayTag, IntTag, LongTag, NamedTag, StringTag, load = _import_amulet_nbt()
    if data.file_path is None:
        raise ValueError("file_path is empty, cannot save.")
    src = Path(data.file_path)
    dst = Path(output_path) if output_path is not None else src

    nbt: NamedTag = load(str(src), compressed=True)
    root = nbt.tag
    metadata = root.get("Metadata")
    if metadata is None:
        raise ValueError("Invalid litematic: missing Metadata compound.")

    metadata["Author"] = StringTag(data.author)
    metadata["Description"] = StringTag(data.description)
    metadata["PreviewImageData"] = IntArrayTag([_to_int32_signed(v) for v in data.preview_image_data])

    if "TimeModified" in metadata:
        metadata["TimeModified"] = LongTag(int(data.modified_unix))
    else:
        metadata["TimeModified"] = IntTag(int(data.modified_unix))

    nbt.save_to(str(dst), compressed=True)
    return dst
