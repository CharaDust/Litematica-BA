"""为 Deepslate ``VoxelRenderer`` 生成体素列表（与正交预览相同的方块着色策略）。"""

from __future__ import annotations

from pathlib import Path

from litematicaba.core.litematic_ortho_preview import _block_id, _is_air, _rgba_for_block

_MAX_REGION_CELLS = 50_000_000
_DEFAULT_MAX_VOXELS = 220_000


def build_region_voxels_payload(
    path: str | Path,
    region_name: str,
    *,
    max_voxels: int = _DEFAULT_MAX_VOXELS,
) -> tuple[dict | None, str]:
    """返回 ``(payload, err)``。

    ``payload`` 含 ``voxels``（``{x,y,z,color:[r,g,b]}``，整数格点、0–255 色）、
    ``camDist``、可选 ``note``（抽样说明）。成功时 ``err`` 为空串。
    """
    from litemapy import Schematic

    p = Path(path)
    try:
        schematic = Schematic.load(str(p))
    except Exception as exc:
        return None, f"无法加载投影：{exc}"

    region = schematic.regions.get(region_name)
    if region is None:
        return None, f"找不到子区域：{region_name!r}"

    sx = region.maxx() - region.minx() + 1
    sy = region.maxy() - region.miny() + 1
    sz = region.maxz() - region.minz() + 1
    if sx <= 0 or sy <= 0 or sz <= 0:
        return None, "子区域尺寸无效。"

    if sx * sy * sz > _MAX_REGION_CELLS:
        return None, f"子区域体素过多（{sx * sy * sz}），请换较小区域或后续版本再试。"

    total_cells = sx * sy * sz
    step = 1
    if total_cells > max_voxels * 6:
        step = max(1, int(round((total_cells / max_voxels) ** (1.0 / 3.0))))

    voxels: list[dict[str, object]] = []
    note_parts: list[str] = []
    if step > 1:
        note_parts.append(f"体素过密，已按 {step} 格步进抽样")

    ox = (sx - 1) / 2.0
    oy = (sy - 1) / 2.0
    oz = (sz - 1) / 2.0

    for ix in range(0, sx, step):
        for iy in range(0, sy, step):
            for iz in range(0, sz, step):
                bid = _block_id(region, ix, iy, iz)
                if _is_air(bid):
                    continue
                r, g, b, _a = _rgba_for_block(bid)
                voxels.append(
                    {
                        "x": int(round(ix - ox)),
                        "y": int(round(iy - oy)),
                        "z": int(round(iz - oz)),
                        "color": [r, g, b],
                    }
                )

    if len(voxels) > max_voxels:
        k = max(1, (len(voxels) + max_voxels - 1) // max_voxels)
        voxels = voxels[::k][:max_voxels]
        note_parts.append(f"已截断至约 {max_voxels} 个体素")

    m = max(sx, sy, sz)
    cam_dist = max(24.0, float(m) * 1.85)

    note = "；".join(note_parts) if note_parts else ""
    payload: dict[str, object] = {
        "voxels": voxels,
        "camDist": cam_dist,
        "bounds": {"sx": sx, "sy": sy, "sz": sz},
    }
    if note:
        payload["note"] = note
    return payload, ""
