# -*- coding: utf-8 -*-
"""
验证紧急遮挡（F5 blackout）。

用 offscreen 平台真实创建遮罩窗口，
检查：模式正确、强度是 0.98 而不是滑块值、再次按下能关闭、
并且不影响原有两种模式。
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication

import privacy_engine
import settings_store

CHECK = []


def check(name, ok, detail=""):
    CHECK.append((name, bool(ok)))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def main():
    # 用临时配置，不碰用户真实设置
    real = settings_store.config_path
    here = os.path.dirname(os.path.abspath(__file__))
    tmpdir = os.path.join(here, ".blackout_tmp")
    os.makedirs(tmpdir, exist_ok=True)
    settings_store.config_path = lambda: os.path.join(tmpdir, "cfg.json")

    app = QApplication(sys.argv)
    ui = privacy_engine.PrivacyAssistantUI()
    ui.show()
    ui.slider.setValue(30)          # 故意设成"轻度"，看紧急遮挡会不会被它拖累
    app.processEvents()

    print("== 1. 紧急遮挡 ==")
    ui._toggle_blackout()
    app.processEvents()
    ov = ui._overlay
    check("遮罩已创建", ov is not None)
    check("模式为 blackout", ov is not None and ov.mode == "blackout",
          ov.mode if ov else "None")
    check("强度是 0.98 而不是 0.30",
          ov is not None and abs(ov.intensity - 0.98) < 0.01,
          f"{ov.intensity:.2f}" if ov else "None")
    check("隐私状态已开启", ui.privacy_active is True)
    check("滑块值未被改动", ui.slider.value() == 30, str(ui.slider.value()))

    print("== 2. 再按一次关闭 ==")
    ui._toggle_blackout()
    app.processEvents()
    check("隐私状态已关闭", ui.privacy_active is False)
    check("模式回到 none", ui.privacy_mode == "none", ui.privacy_mode)

    print("== 3. 原有模式不受影响 ==")
    ui._toggle_circle()
    app.processEvents()
    check("圆形模式仍可用", ui._overlay is not None and ui._overlay.mode == "circle",
          ui._overlay.mode if ui._overlay else "None")
    check("圆形模式强度回到滑块值",
          ui._overlay is not None and abs(ui._overlay.intensity - 0.30) < 0.01,
          f"{ui._overlay.intensity:.2f}" if ui._overlay else "None")

    print("== 4. 切到紧急遮挡再切回来 ==")
    ui._toggle_blackout()
    app.processEvents()
    check("切换后为 blackout", ui._overlay.mode == "blackout", ui._overlay.mode)
    check("切换后强度 0.98", abs(ui._overlay.intensity - 0.98) < 0.01,
          f"{ui._overlay.intensity:.2f}")

    ui.close()
    app.processEvents()

    settings_store.config_path = real
    for f in os.listdir(tmpdir):
        try:
            os.remove(os.path.join(tmpdir, f))
        except OSError:
            pass
    try:
        os.rmdir(tmpdir)
    except OSError:
        pass

    passed = sum(1 for _, ok in CHECK if ok)
    print(f"\n{passed}/{len(CHECK)} 通过")
    return 0 if passed == len(CHECK) else 1


if __name__ == "__main__":
    sys.exit(main())
