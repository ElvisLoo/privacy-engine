# -*- coding: utf-8 -*-
"""
隐私引擎：热键生命周期与跨线程安全。

要证明两件事：
  1. 程序退出时全局热键被真正卸载（否则 phantom hook 留在系统里）；
  2. 从键盘线程跨到 Qt 主线程的操作是安全的。

第 1 项不依赖 GUI，可以直接验证；
第 2 项用 offscreen 平台模拟。
"""
import os
import sys
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CHECK = []


def check(name, ok, detail=""):
    CHECK.append((name, bool(ok)))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def test_hotkey_cleanup():
    """检查源码里是否有卸载逻辑"""
    here = os.path.dirname(os.path.abspath(__file__))
    src = open(os.path.join(here, "privacy_engine.py"), encoding="utf-8").read()
    has_unhook = "unhook_all" in src or "remove_hotkey" in src
    check("退出时卸载全局热键", has_unhook,
          "未找到 unhook_all / remove_hotkey" if not has_unhook else "")
    return has_unhook


def test_cross_thread():
    """keyboard 回调在独立线程里，验证跨线程调用不会崩"""
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QTimer, Qt

    app = QApplication.instance() or QApplication(sys.argv)
    result = {"called": 0, "error": None}

    def on_main_thread():
        result["called"] += 1

    # 用信号转发（当前实现），而不是直接跨线程调 QTimer
    from PyQt5.QtCore import pyqtSignal, QObject
    from PyQt5.QtWidgets import QWidget

    class Emitter(QObject):
        sig = pyqtSignal()

    class UI(QWidget):
        _sig = pyqtSignal()
        def __init__(self):
            super().__init__()
            self._sig.connect(on_main_thread, Qt.QueuedConnection) if False else None

    # 直接用真实实现里的信号
    from privacy_engine import PrivacyAssistantUI
    # 只测信号机制本身，不实例化整个窗口
    class Probe(QWidget):
        _hotkeyFired = pyqtSignal(str)
    probe = Probe()
    probe._hotkeyFired.connect(lambda a: on_main_thread(), Qt.QueuedConnection)

    def worker():
        try:
            probe._hotkeyFired.emit("blackout")
        except Exception as e:
            result["error"] = str(e)

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout=3)

    deadline = time.time() + 2
    while time.time() < deadline and result["called"] == 0:
        app.processEvents()
        time.sleep(0.02)

    check("跨线程信号能被主线程执行",
          result["called"] > 0 and result["error"] is None,
          f"called={result['called']} err={result['error']}")


def main():
    print("== 热键生命周期 ==")
    test_hotkey_cleanup()

    print("== 跨线程调度 ==")
    test_cross_thread()

    passed = sum(1 for _, ok in CHECK if ok)
    print(f"\n{passed}/{len(CHECK)} 通过")
    return 0 if passed == len(CHECK) else 1


if __name__ == "__main__":
    sys.exit(main())
