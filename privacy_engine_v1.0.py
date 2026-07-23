import sys
import os
import traceback

try:
    from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QSlider, QHBoxLayout, QVBoxLayout, QDesktopWidget
    from PyQt5.QtCore import Qt, QTimer, QRect, QPoint, QSize
    from PyQt5.QtGui import QPainter, QColor, QLinearGradient, QFont, QFontMetrics, QPainterPath, QBrush, QPen
    from PyQt5.QtGui import QCursor
    import keyboard
    import webbrowser
    print("All imports OK")
except Exception as e:
    print(f"[IMPORT ERROR] {e}")
    traceback.print_exc()
    input("Press Enter to exit...")
    sys.exit(1)


def font_size(base):
    try:
        app = QApplication.instance()
        if app is None: return base
        screen = app.primaryScreen()
        if screen is None: return base
        dpi = screen.logicalDotsPerInch()
        scale = dpi / 96.0
        return max(base, int(base * scale))
    except Exception:
        return base


def px(base):
    try:
        app = QApplication.instance()
        if app is None: return base
        screen = app.primaryScreen()
        if screen is None: return base
        dpi = screen.logicalDotsPerInch()
        scale = dpi / 96.0
        return max(base, int(base * scale))
    except Exception:
        return base


SLIDER_STYLE = """
QSlider::groove:horizontal {
    border: none; height: %dpx; background: #e0e0e0; border-radius: %dpx;
}
QSlider::handle:horizontal {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #2979ff, stop:1 #448aff);
    width: %dpx; height: %dpx; margin: -%dpx 0;
    border-radius: %dpx; border: 3px solid #ffffff;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1565c0, stop:1 #2979ff);
    border-radius: %dpx;
}
""" % (px(8), px(4), px(22), px(22), px(7), px(11), px(4))


class StatCard(QWidget):
    def __init__(self, label, value, color="#2979ff"):
        super().__init__()
        self._label = label
        self._value = value
        self._color = color
        self.setFixedHeight(px(60))

    def set_value(self, v):
        self._value = v; self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setFont(QFont("Microsoft YaHei", font_size(8)))
        p.setPen(QColor("#90a4ae"))
        p.drawText(QRect(0, px(8), w, px(18)), Qt.AlignCenter, self._label)
        p.setFont(QFont("Microsoft YaHei", font_size(18), QFont.Bold))
        p.setPen(QColor(self._color))
        p.drawText(QRect(0, px(28), w, px(32)), Qt.AlignCenter, self._value)


class OverlayWindow(QWidget):
    def __init__(self, geo):
        super().__init__()
        self.intensity = 0.5
        self.radius = px(150)

        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setGeometry(geo)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)

    def showEvent(self, event):
        self._timer.start(33)
        super().showEvent(event)

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def set_intensity(self, val):
        self.intensity = val

    def paintEvent(self, event):
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            w, h = self.width(), self.height()

            cursor = QCursor.pos()
            g = QApplication.primaryScreen().geometry()
            mx = cursor.x() - g.x()
            my = cursor.y() - g.y()
            r = self.radius

            path = QPainterPath()
            path.addRect(0, 0, w, h)
            circle = QPainterPath()
            circle.addEllipse(mx - r, my - r, r * 2, r * 2)
            mask = path.subtracted(circle)

            alpha = int(self.intensity * 255)
            p.fillPath(mask, QColor(0, 0, 0, alpha))
        except Exception as e:
            print(f"[Overlay paint error] {e}")


class PrivacyAssistantUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("防窥助手")
        self.setFixedSize(px(420), px(720))
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.privacy_active = False
        self.intensity = 0.5
        self._overlay = None
        self._drag_pos = None
        self._init_ui()
        self._center()

    def _center(self):
        f = self.frameGeometry()
        c = QDesktopWidget().availableGeometry().center()
        f.moveCenter(c)
        self.move(f.topLeft())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(px(16), px(16), px(16), px(16))
        root.setSpacing(px(12))

        card = QWidget()
        card.setObjectName("mainCard")
        card.setStyleSheet("""
            #mainCard {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #ffffff, stop:1 #f5f5f5);
                border-radius: %dpx;
                border: 1px solid #e0e0e0;
            }
        """ % px(16))
        lay = QVBoxLayout(card)
        lay.setContentsMargins(px(22), px(20), px(22), px(20))
        lay.setSpacing(px(12))

        # ---- 标题栏 ----
        tb = QHBoxLayout()
        icon = QLabel(" ")
        icon.setFont(QFont("Segoe UI Emoji", font_size(13)))
        tb.addWidget(icon)
        t = QLabel("防窥助手 v1.0")
        t.setFont(QFont("Microsoft YaHei", font_size(11), QFont.Bold))
        t.setStyleSheet("color:#1a1a2e;")
        tb.addWidget(t)
        by_label = QLabel("by ")
        by_label.setFont(QFont("Microsoft YaHei", font_size(9)))
        by_label.setStyleSheet("color:#90a4ae;")
        tb.addWidget(by_label)
        link_btn = QPushButton("极客港")
        link_btn.setFont(QFont("Microsoft YaHei", font_size(9)))
        link_btn.setStyleSheet("QPushButton{background:transparent;border:none;color:#2979ff;text-decoration:underline;font-weight:bold;}")
        link_btn.clicked.connect(lambda: webbrowser.open("https://www.jikegang.com/"))
        tb.addWidget(link_btn)
        tb.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(px(28), px(28))
        style = (
            "QPushButton{background:transparent;border:none;color:#aaa;"
            "font-size:%dpx;font-weight:bold;}"
            "QPushButton:hover{color:#ff5252;background:#ffe0e0;border-radius:%dpx;}"
        ) % (font_size(14), px(14))
        close_btn.setStyleSheet(style)
        close_btn.clicked.connect(self.close)
        tb.addWidget(close_btn)
        lay.addLayout(tb)
        lay.addSpacing(px(8))

        # ---- 副标题 ----
        sub = QLabel("PRIVACY ENGINE")
        sub.setAlignment(Qt.AlignCenter)
        sub.setFont(QFont("Consolas", font_size(10), QFont.Bold))
        sub.setStyleSheet("color:#2979ff;letter-spacing:3px;")
        lay.addWidget(sub)
        lay.addSpacing(px(4))
        big = QLabel("防窥助手")
        big.setAlignment(Qt.AlignCenter)
        big.setFont(QFont("Microsoft YaHei", font_size(20), QFont.Bold))
        big.setStyleSheet("color:#1a1a2e;")
        lay.addWidget(big)
        lay.addSpacing(px(2))
        desc = QLabel("动态视线隔离 · 局部可视化防护")
        desc.setAlignment(Qt.AlignCenter)
        desc.setFont(QFont("Microsoft YaHei", font_size(8)))
        desc.setStyleSheet("color:#78909c;")
        lay.addWidget(desc)
        lay.addSpacing(px(10))

        # ---- 检测卡片 ----
        dc = QWidget()
        dc.setObjectName("detectCard")
        dc.setStyleSheet("#detectCard{background:#f5f0eb;border-radius:%dpx;border:1px solid #e8e0d8;}" % px(12))
        dl = QVBoxLayout(dc)
        dl.setContentsMargins(px(16), px(14), px(16), px(14))
        dl.setSpacing(px(6))
        dt = QLabel("实时屏幕暴露检测")
        dt.setAlignment(Qt.AlignCenter)
        dt.setFont(QFont("Microsoft YaHei", font_size(9), QFont.Bold))
        dt.setStyleSheet("color:#37474f;")
        dl.addWidget(dt)

        self.mockup_label = QLabel()
        self.mockup_label.setFixedHeight(px(90))
        self.mockup_label.setAlignment(Qt.AlignCenter)
        self.mockup_label.setStyleSheet(
            "background:#f5f0eb; border-radius:%dpx;"
            "color:#37474f; font-size:%dpx; font-family:Microsoft YaHei;" % (px(8), font_size(12))
        )
        self.mockup_label.setText("🔒 圆形可视区域模式\n鼠标周围 300px 可见")
        dl.addWidget(self.mockup_label)

        srow = QHBoxLayout()
        srow.setSpacing(0)
        self.s2 = StatCard("屏幕暴露", "100%", "#ff9800")
        self.s3 = StatCard("泄露概率", "86%", "#ff5252")
        self.s4 = StatCard("防护状态", "裸屏", "#ff5252")
        for s in [self.s2, self.s3, self.s4]:
            srow.addWidget(s)
        dl.addLayout(srow)
        lay.addWidget(dc)

        # ---- 强度滑块 ----
        sl = QHBoxLayout()
        sl.setContentsMargins(px(4), 0, px(4), 0)
        sl_label = QLabel("防窥强度")
        sl_label.setFont(QFont("Microsoft YaHei", font_size(10), QFont.Bold))
        sl_label.setStyleSheet("color:#37474f;")
        sl.addWidget(sl_label)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setValue(80)
        self.slider.setStyleSheet(SLIDER_STYLE)
        self.slider.valueChanged.connect(self._on_slider)
        sl.addWidget(self.slider, 1)
        self.sl_val = QLabel("极致 · 80%")
        self.sl_val.setFont(QFont("Microsoft YaHei", font_size(9)))
        self.sl_val.setStyleSheet("color:#2979ff;font-weight:bold;")
        self.sl_val.setFixedWidth(px(80))
        self.sl_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        sl.addWidget(self.sl_val)
        lay.addLayout(sl)
        lay.addSpacing(px(8))

        # ---- 主按钮 ----
        self.btn = QPushButton("开启防窥")
        self.btn.setFixedHeight(px(50))
        self.btn.setCursor(Qt.PointingHandCursor)
        self._set_btn_blue()
        self.btn.clicked.connect(self._toggle)
        lay.addWidget(self.btn)
        lay.addSpacing(px(20))

        # ---- 底部声明 ----
        foot = QLabel("LOCAL PRIVACY MODEL · NO CAMERA · NO DATA UPLOAD")
        foot.setAlignment(Qt.AlignCenter)
        foot.setFont(QFont("Consolas", font_size(7)))
        foot.setStyleSheet("color:#b0bec5;letter-spacing:1px;")
        lay.addWidget(foot)

        root.addWidget(card)

        hint = QLabel("F6 开关  |  F7 降低强度  |  F8 提高强度")
        hint.setAlignment(Qt.AlignCenter)
        hint.setFont(QFont("Microsoft YaHei", font_size(8)))
        hint.setStyleSheet("color:rgba(255,255,255,120);margin-top:8px;")
        root.addWidget(hint)

    def _set_btn_blue(self):
        style = (
            "QPushButton{"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #1565c0,stop:0.5 #2979ff,stop:1 #42a5f5);"
            "color:white;border:none;border-radius:%dpx;"
            "font-size:%dpx;font-weight:bold;font-family:\"Microsoft YaHei\";"
            "}QPushButton:hover{"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #1976d2,stop:0.5 #42a5f5,stop:1 #64b5f6);"
            "}"
        ) % (px(25), font_size(15))
        self.btn.setStyleSheet(style)

    def _set_btn_red(self):
        style = (
            "QPushButton{"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #b71c1c,stop:0.5 #f44336,stop:1 #ef5350);"
            "color:white;border:none;border-radius:%dpx;"
            "font-size:%dpx;font-weight:bold;font-family:\"Microsoft YaHei\";"
            "}QPushButton:hover{"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #c62828,stop:0.5 #e53935,stop:1 #f44336);"
            "}"
        ) % (px(25), font_size(15))
        self.btn.setStyleSheet(style)

    def _on_slider(self, v):
        self.intensity = v / 100.0
        tag = "轻度" if v < 33 else ("标准" if v < 66 else "极致")
        self.sl_val.setText(f"{tag} · {v}%")
        self._update_stats()
        if self.privacy_active and self._overlay is not None:
            self._overlay.set_intensity(self.intensity)

    def _update_stats(self):
        """根据当前强度实时更新屏幕暴露和泄露概率"""
        exp = 100 - int(self.intensity * 100)
        self.s2.set_value(f"{exp}%")
        self.s3.set_value(f"{max(0, 86 - int(self.intensity * 80))}%")

    def _toggle(self):
        self.privacy_active = not self.privacy_active
        if self.privacy_active:
            self.btn.setText("关闭防窥")
            self._set_btn_red()
            self._stats_on()
            self._show_overlay()
        else:
            self.btn.setText("开启防窥")
            self._set_btn_blue()
            self._stats_off()
            self._hide_overlay()

    def _stats_on(self):
        self._update_stats()
        self.s4.set_value("防护中")
        self.s4._color = "#4caf50"

    def _stats_off(self):
        self._update_stats()
        self.s4.set_value("裸屏")
        self.s4._color = "#ff5252"

    def _show_overlay(self):
        if self._overlay is None:
            geo = QApplication.primaryScreen().geometry()
            self._overlay = OverlayWindow(geo)
        self._overlay.set_intensity(self.intensity)
        self._overlay.showFullScreen()

    def _hide_overlay(self):
        if self._overlay is not None:
            self._overlay.hide()

    def paintEvent(self, event):
        pass


def main():
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        app = QApplication(sys.argv)
        app.setFont(QFont("Microsoft YaHei", font_size(9)))

        ui = PrivacyAssistantUI()
        ui.show()

        keyboard.add_hotkey("F6", ui._toggle)
        keyboard.add_hotkey("F7", lambda: ui.slider.setValue(max(0, ui.slider.value() - 5)))
        keyboard.add_hotkey("F8", lambda: ui.slider.setValue(min(100, ui.slider.value() + 5)))

        print("=" * 40)
        print("  防窥助手")
        print("=" * 40)
        print("  F6  开关防窥")
        print("  F7  降低强度")
        print("  F8  提高强度")
        print("=" * 40)
        sys.stdout.flush()

        sys.exit(app.exec_())
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()