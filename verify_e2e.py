# -*- coding: utf-8 -*-
"""
端到端验证：真实创建窗口，确认核心交互与配置持久化。

用 offscreen 平台跑，不需要显示器 —— 但走的是和真机完全相同的代码路径
（真实的 QWidget 构造、真实的绘制事件、真实的 closeEvent）。

不是单元测试的替代品：单元测试测的是纯函数，
这里测的是"把窗口建起来、拖一拖、关掉，配置真的写到磁盘了吗"。

运行：python verify_e2e.py
"""

import json
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication  # noqa: E402

import privacy_engine  # noqa: E402
import settings_store  # noqa: E402

CHECK = []


def check(name, ok, detail=""):
    CHECK.append((name, bool(ok), detail))
    print(f"  {'PASS' if ok else 'FAIL'} {name}" + (f"  [{detail}]" if detail else ""))


def main():
    # 用一个临时配置路径，避免污染用户真实设置
    real_path = settings_store.config_path
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".e2e_tmp")
    os.makedirs(test_dir, exist_ok=True)
    settings_store.config_path = lambda: os.path.join(test_dir, "cfg.json")
    for f in os.listdir(test_dir):
        try:
            os.remove(os.path.join(test_dir, f))
        except OSError:
            pass

    app = QApplication(sys.argv)

    print("== 1. 首次启动（无配置文件）==")
    ui = privacy_engine.PrivacyAssistantUI()
    ui.show()
    app.processEvents()
    check("窗口建起来了", ui.width() > 0 and ui.height() > 0, f"{ui.width()}x{ui.height()}")
    check("滑块用默认值 50", ui.slider.value() == 50, str(ui.slider.value()))

    print("== 2. 调强度 ==")
    ui.slider.setValue(73)
    app.processEvents()
    check("强度跟随滑块", abs(ui.intensity - 0.73) < 0.01, f"{ui.intensity:.2f}")
    check("状态文案更新", "73%" in ui.sl_val.text(), ui.sl_val.text())

    print("== 3. 开启圆形防窥 ==")
    ui._toggle_circle()
    app.processEvents()
    check("遮罩已创建", ui._overlay is not None)
    if ui._overlay:
        check("遮罩模式为 circle", ui._overlay.mode == "circle", ui._overlay.mode)
        check("遮罩继承了强度", abs(ui._overlay.intensity - 0.73) < 0.01, f"{ui._overlay.intensity:.2f}")

    print("== 4. 切到三区域 ==")
    ui._toggle_zone()
    app.processEvents()
    check("模式切换为 three_zone", ui._overlay is not None and ui._overlay.mode == "three_zone",
          ui._overlay.mode if ui._overlay else "None")

    print("== 5. 移动窗口后关闭，检查落盘 ==")
    ui.move(321, 123)
    app.processEvents()
    ui.close()
    app.processEvents()

    saved = settings_store.load()
    check("强度已保存", saved["intensity"] == 73, str(saved["intensity"]))
    check("模式已保存", saved["mode"] == "three_zone", saved["mode"])
    check("位置已保存", (saved["window_x"], saved["window_y"]) == (321, 123),
          str((saved["window_x"], saved["window_y"])))

    print("== 6. 重启后恢复 ==")
    ui2 = privacy_engine.PrivacyAssistantUI()
    ui2.show()
    app.processEvents()
    check("滑块恢复为 73", ui2.slider.value() == 73, str(ui2.slider.value()))
    check("窗口位置恢复", (ui2.pos().x(), ui2.pos().y()) == (321, 123),
          str((ui2.pos().x(), ui2.pos().y())))
    ui2.close()
    app.processEvents()

    # 还原真实配置路径，清理测试文件
    settings_store.config_path = real_path
    for f in os.listdir(test_dir):
        try:
            os.remove(os.path.join(test_dir, f))
        except OSError:
            pass
    try:
        os.rmdir(test_dir)
    except OSError:
        pass

    passed = sum(1 for _, ok, _ in CHECK if ok)
    total = len(CHECK)
    print(f"\n{passed}/{total} 通过")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
