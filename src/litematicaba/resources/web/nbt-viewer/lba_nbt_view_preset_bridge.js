/**
 * 与渲染页九向预设（0..8）对齐，驱动 vscode-nbt StructureEditor 的轨道角 cRot。
 * 与 FOV 滑动条（0..110，0 为正交）同步 cFovDeg。
 * 依赖 editor.js 将主 Editor 实例挂在 window.__lbaNbtEditor。
 */
(function () {
  if (typeof window.__lbaCameraFov !== "number") {
    window.__lbaCameraFov = 70;
  }
  function norm3(x, y, z) {
    var len = Math.hypot(x, y, z);
    if (len < 1e-8) {
      return [0, 1, 0];
    }
    return [x / len, y / len, z / len];
  }

  /** 与 deepslate_viewer.html 中 presetDirection 一致（相机相对目标的偏移方向） */
  function presetDir(p) {
    var d = 1;
    var dh = 0.45;
    switch (p | 0) {
      case 0:
        return norm3(0, 1, 0);
      case 1:
        return norm3(0, dh, -d);
      case 2:
        return norm3(0, dh, d);
      case 3:
        return norm3(-d, dh, 0);
      case 4:
        return norm3(d, dh, 0);
      case 5:
        return norm3(d * 0.82, d * 0.55, -d * 0.82);
      case 6:
        return norm3(d * 0.82, d * 0.55, d * 0.82);
      case 7:
        return norm3(-d * 0.82, d * 0.55, d * 0.82);
      default:
        return norm3(-d * 0.82, d * 0.55, -d * 0.82);
    }
  }

  /**
   * StructureEditor.getViewMatrix：T(0,0,-cDist)*Rx(cRot[1])*Ry(cRot[0])*T(cPos)
   * 与 Deepslate 页用同一视线方向推导 yaw/pitch（可能需微调符号）。
   */
  function presetToYawPitch(p) {
    var dir = presetDir(p);
    if ((p | 0) === 0) {
      return [0, Math.PI / 2 - 0.05];
    }
    var yaw = Math.atan2(dir[0], dir[2]);
    var pitch = Math.asin(Math.max(-1, Math.min(1, dir[1])));
    return [yaw, pitch];
  }

  /** 与 Editor.type 对应：structure / chunk 均使用 StructureEditor 系 3D（ChunkEditor 继承自 StructureEditor） */
  function lbaStructureLikePanelKey(ed) {
    if (!ed) {
      return null;
    }
    if (ed.type === "chunk") {
      return "chunk";
    }
    if (ed.type === "structure") {
      return "structure";
    }
    return null;
  }

  function lbaGetStructureLikeEditor(ed) {
    var key = lbaStructureLikePanelKey(ed);
    if (!key || !ed.panels || !ed.panels[key]) {
      return null;
    }
    try {
      return ed.panels[key].editor();
    } catch (e) {
      return null;
    }
  }

  window.lbaSetViewPreset = function (n) {
    var ed = window.__lbaNbtEditor;
    var se = lbaGetStructureLikeEditor(ed);
    if (!se || !se.cRot) {
      return;
    }
    var p = Math.max(0, Math.min(8, n | 0));
    var yp = presetToYawPitch(p);
    se.cRot[0] = yp[0];
    se.cRot[1] = yp[1];
    if (typeof se.render === "function") {
      se.render();
    }
  };

  window.lbaSetCameraFov = function (deg) {
    var v = Math.max(0, Math.min(110, deg | 0));
    window.__lbaCameraFov = v;
    var ed = window.__lbaNbtEditor;
    var se = lbaGetStructureLikeEditor(ed);
    if (!se) {
      return;
    }
    se.cFovDeg = v;
    if (typeof se.render === "function") {
      se.render();
    }
  };
})();
