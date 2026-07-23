import sys
import os
import random
import traceback

try:
    from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QSlider, QHBoxLayout, QVBoxLayout, QDesktopWidget, QFrame
    from PyQt5.QtCore import Qt, QTimer, QRect, QPoint, QSize, QEvent
    from PyQt5.QtGui import QPainter, QColor, QLinearGradient, QFont, QFontMetrics, QPainterPath, QBrush, QPen
    from PyQt5.QtGui import QCursor
    import keyboard
    import webbrowser
    print("All imports OK")
except Exception as e:
    print(f"[IMPORT ERROR] {e}")
    traceback.print_exc()
    try:
        input("Press Enter to exit...")
    except Exception:
        pass
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
QSlider::groove:horizontal:disabled {
    background: #e8e8e8;
}
QSlider::handle:horizontal:disabled {
    background: #cccccc;
    border: 3px solid #e0e0e0;
}
QSlider::sub-page:horizontal:disabled {
    background: #e8e8e8;
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
    def __init__(self, geo, mode="circle"):
        super().__init__()
        self.intensity = 0.5
        self.radius = px(150)
        self.mode = mode  # "circle" or "three_zone"

        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput
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

            if self.mode == "three_zone":
                self._paint_three_zone(p, w, h)
            else:
                self._paint_circle(p, w, h)
        except Exception as e:
            print(f"[Overlay paint error] {e}")

    def _paint_circle(self, p, w, h):
        """圆形可视区域模式"""
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

    def _paint_three_zone(self, p, w, h):
        """左中右三区域渐变模式"""
        alpha = int(self.intensity * 255)
        tw = int(w * 0.08)
        l1 = int(w / 3 - tw)
        l2 = int(w / 3 + tw)
        r1 = int(w * 2 / 3 - tw)
        r2 = int(w * 2 / 3 + tw)

        # 左暗区
        p.fillRect(0, 0, l1, h, QColor(0, 0, 0, alpha))

        # 左侧过渡：暗→透明
        lw = l2 - l1
        if lw > 0:
            lg = QLinearGradient(0, 0, lw, 0)
            lg.setColorAt(0.0, QColor(0, 0, 0, alpha))
            lg.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.save()
            p.translate(l1, 0)
            p.fillRect(0, 0, lw, h, lg)
            p.restore()

        # 中间亮区（不遮罩）
        # 不需要绘制，保持透明

        # 右侧过渡：透明→暗
        rw = r2 - r1
        if rw > 0:
            rg = QLinearGradient(0, 0, rw, 0)
            rg.setColorAt(0.0, QColor(0, 0, 0, 0))
            rg.setColorAt(1.0, QColor(0, 0, 0, alpha))
            p.save()
            p.translate(r1, 0)
            p.fillRect(0, 0, rw, h, rg)
            p.restore()

        # 右暗区
        p.fillRect(r2, 0, w - r2, h, QColor(0, 0, 0, alpha))


class PrivacyAssistantUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("防窥助手")
        self.setFixedSize(px(420), px(650))
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.privacy_active = False
        self.privacy_mode = "none"  # "circle" or "three_zone"
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

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMinimized:
                if self._overlay is not None:
                    self._overlay.hide()
            else:
                if self.privacy_active and self._overlay is not None:
                    self._overlay.showFullScreen()
        super().changeEvent(event)

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(px(16), px(12), px(16), px(12))
        root.setSpacing(px(10))

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
        lay.setContentsMargins(px(22), px(16), px(22), px(24))
        lay.setSpacing(px(10))

        # ---- 标题栏 ----
        tb = QHBoxLayout()
        icon = QLabel(" ")
        icon.setFont(QFont("Segoe UI Emoji", font_size(13)))
        tb.addWidget(icon)
        tb.addStretch()
        min_btn = QPushButton("─")
        min_btn.setFixedSize(px(28), px(28))
        min_style = (
            "QPushButton{background:transparent;border:none;color:#aaa;"
            "font-size:%dpx;font-weight:bold;}"
            "QPushButton:hover{color:#2979ff;background:#e3f2fd;border-radius:%dpx;}"
        ) % (font_size(14), px(14))
        min_btn.setStyleSheet(min_style)
        min_btn.clicked.connect(self.showMinimized)
        tb.addWidget(min_btn)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(px(28), px(28))
        close_style = (
            "QPushButton{background:transparent;border:none;color:#aaa;"
            "font-size:%dpx;font-weight:bold;}"
            "QPushButton:hover{color:#ff5252;background:#ffe0e0;border-radius:%dpx;}"
        ) % (font_size(14), px(14))
        close_btn.setStyleSheet(close_style)
        close_btn.clicked.connect(self.close)
        tb.addWidget(close_btn)
        lay.addLayout(tb)
        lay.addSpacing(px(2))

        big = QLabel("防窥助手")
        big.setAlignment(Qt.AlignCenter)
        big.setFont(QFont("Microsoft YaHei", font_size(22), QFont.Bold))
        big.setStyleSheet("color:#1a1a2e;")
        lay.addWidget(big)
        lay.addSpacing(px(1))
        eng = QLabel("PRIVACY ENGINE")
        eng.setAlignment(Qt.AlignCenter)
        eng.setFont(QFont("Consolas", font_size(10), QFont.Bold))
        eng.setStyleSheet("color:#2979ff;letter-spacing:2px;")
        lay.addWidget(eng)
        lay.addSpacing(px(1))
        desc = QLabel(random.choice([
            "动态视线隔离 · 局部可视化防护",
            "你的屏幕 · 你的隐私 · 你的掌控",
            "侧目无畏 · 凝视无忧",
            "防窥黑科技 · 懂你更护你",
            "隐私不设限 · 视野更自由",
            "看得见的安心 · 看不见的守护",
            "一键防窥 · 全屏无虑",
            "左右兼顾 · 中心更亮",
        ]))
        desc.setAlignment(Qt.AlignCenter)
        desc.setFont(QFont("Microsoft YaHei", font_size(9)))
        desc.setStyleSheet("color:#78909c;")
        lay.addWidget(desc)
        lay.addSpacing(px(8))

        # ---- 检测卡片 ----
        dc = QWidget()
        dc.setObjectName("detectCard")
        dc.setStyleSheet("#detectCard{background:#f5f0eb;border-radius:%dpx;border:1px solid #e8e0d8;}" % px(12))
        dl = QVBoxLayout(dc)
        dl.setContentsMargins(px(14), px(10), px(14), px(10))
        dl.setSpacing(px(4))

        self.mockup_label = QLabel()
        self.mockup_label.setFixedHeight(px(70))
        self.mockup_label.setAlignment(Qt.AlignCenter)
        self.mockup_label.setStyleSheet(
            "background:#f5f0eb; border-radius:%dpx;"
            "color:#37474f; font-size:%dpx; font-family:Microsoft YaHei;" % (px(8), font_size(12))
        )
        self.mockup_label.setText("🔒 防窥模式\n圆形可视 / 左右三区域")
        dl.addWidget(self.mockup_label)

        hint = QLabel("F6 全屏防窥  |  F7 左右防窥  |  F8 降低强度  |  F9 提高强度")
        hint.setAlignment(Qt.AlignCenter)
        hint.setFont(QFont("Microsoft YaHei", font_size(8)))
        hint.setStyleSheet("color:#90a4ae;padding:2px 0;")
        dl.addWidget(hint)

        srow = QHBoxLayout()
        srow.setSpacing(0)
        self.s2 = StatCard("屏幕暴露", "100%", "#ff9800")
        self.s3 = StatCard("泄露概率", "96%", "#ff5252")
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
        self.slider.setValue(50)
        self.slider.setStyleSheet(SLIDER_STYLE)
        self.slider.valueChanged.connect(self._on_slider)
        sl.addWidget(self.slider, 1)
        self.sl_val = QLabel("标准 · 50%")
        self.sl_val.setFont(QFont("Microsoft YaHei", font_size(9)))
        self.sl_val.setStyleSheet("color:#2979ff;font-weight:bold;")
        self.sl_val.setFixedWidth(px(80))
        self.sl_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        sl.addWidget(self.sl_val)
        lay.addLayout(sl)
        lay.addSpacing(px(8))

        # ---- 双按钮 ----
        btn_row = QHBoxLayout()
        btn_row.setSpacing(px(8))

        self.btn_circle = QPushButton("开启全屏防窥")
        self.btn_circle.setFixedHeight(px(46))
        self.btn_circle.setCursor(Qt.PointingHandCursor)
        self._set_btn_blue(self.btn_circle)
        self.btn_circle.clicked.connect(self._toggle_circle)
        btn_row.addWidget(self.btn_circle)

        self.btn_zone = QPushButton("开启左右防窥")
        self.btn_zone.setFixedHeight(px(46))
        self.btn_zone.setCursor(Qt.PointingHandCursor)
        self._set_btn_blue(self.btn_zone)
        self.btn_zone.clicked.connect(self._toggle_zone)
        btn_row.addWidget(self.btn_zone)

        lay.addLayout(btn_row)
        lay.addSpacing(px(20))

        # ---- 底部声明 ----
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color:#e0e0e0;")
        line.setFixedHeight(px(1))
        lay.addWidget(line)
        lay.addSpacing(px(4))

        foot = QLabel("LOCAL PRIVACY · NO CAMERA · NO DATA UPLOAD")
        foot.setAlignment(Qt.AlignCenter)
        foot.setFont(QFont("Consolas", font_size(8)))
        foot.setStyleSheet("color:#b0bec5;letter-spacing:1px;")
        lay.addWidget(foot)
        lay.addSpacing(px(2))

        foot_row = QHBoxLayout()
        foot_row.setContentsMargins(0, 0, 0, 0)
        foot_row.setSpacing(0)
        foot_row.addStretch()
        foot_engine = QLabel("PRIVACY ENGINE v2.4")
        foot_engine.setFont(QFont("Consolas", font_size(8), QFont.Bold))
        foot_engine.setStyleSheet("color:#2979ff;letter-spacing:1px;")
        foot_row.addWidget(foot_engine)
        foot_sep = QLabel("  ·  ")
        foot_sep.setFont(QFont("Consolas", font_size(8)))
        foot_sep.setStyleSheet("color:#b0bec5;")
        foot_row.addWidget(foot_sep)
        foot_link = QPushButton("JIKEGANG")
        foot_link.setFont(QFont("Consolas", font_size(8), QFont.Bold))
        foot_link.setStyleSheet("QPushButton{background:transparent;border:none;color:#2979ff;text-decoration:underline;font-weight:bold;}")
        foot_link.clicked.connect(lambda: webbrowser.open("https://www.jikegang.com/"))
        foot_row.addWidget(foot_link)
        foot_row.addStretch()
        lay.addLayout(foot_row)

        root.addWidget(card)

        self._update_buttons()

    def _set_btn_blue(self, btn):
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
        ) % (px(23), font_size(14))
        btn.setStyleSheet(style)

    def _set_btn_red(self, btn):
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
        ) % (px(23), font_size(14))
        btn.setStyleSheet(style)

    def _on_slider(self, v):
        self.intensity = v / 100.0
        tag = "无" if v == 0 else ("轻度" if v < 33 else ("标准" if v < 66 else "极致"))
        self.sl_val.setText(f"{tag} · {v}%")
        self._update_stats()
        self._update_status()
        if self.privacy_active and self._overlay is not None:
            self._overlay.set_intensity(self.intensity)

    def _update_status(self):
        if self.slider.value() <= 0:
            self.s4.set_value("裸屏")
            self.s4._color = "#ff5252"
        else:
            self.s4.set_value("防护中")
            self.s4._color = "#4caf50"

    def _update_stats(self):
        exp = 100 - int(self.intensity * 100)
        self.s2.set_value(f"{exp}%")
        self.s3.set_value(f"{max(3, 96 - int(self.intensity * 93))}%")

    def _update_buttons(self):
        """根据状态更新两个按钮"""
        self.slider.setEnabled(self.privacy_active)
        self.sl_val.setEnabled(self.privacy_active)
        if self.privacy_mode == "circle":
            self.btn_circle.setText("关闭全屏防窥")
            self._set_btn_red(self.btn_circle)
            self.btn_zone.setText("开启左右防窥")
            self._set_btn_blue(self.btn_zone)
        elif self.privacy_mode == "three_zone":
            self.btn_circle.setText("开启全屏防窥")
            self._set_btn_blue(self.btn_circle)
            self.btn_zone.setText("关闭左右防窥")
            self._set_btn_red(self.btn_zone)
        else:
            self.btn_circle.setText("开启全屏防窥")
            self._set_btn_blue(self.btn_circle)
            self.btn_zone.setText("开启左右防窥")
            self._set_btn_blue(self.btn_zone)

    def _toggle_circle(self):
        if self.privacy_mode == "circle":
            # 关闭
            self.privacy_active = False
            self.privacy_mode = "none"
            self._stats_off()
            self._hide_overlay()
        else:
            # 切换到全屏防窥
            self.privacy_active = True
            self.privacy_mode = "circle"
            self._stats_on()
            self._show_overlay("circle")
        self._update_buttons()

    def _toggle_zone(self):
        if self.privacy_mode == "three_zone":
            # 关闭
            self.privacy_active = False
            self.privacy_mode = "none"
            self._stats_off()
            self._hide_overlay()
        else:
            # 切换到左右防窥
            self.privacy_active = True
            self.privacy_mode = "three_zone"
            self._stats_on()
            self._show_overlay("three_zone")
        self._update_buttons()

    def _stats_on(self):
        self._update_stats()
        self._update_status()

    def _stats_off(self):
        self.s2.set_value("100%")
        self.s3.set_value("96%")
        self.s4.set_value("裸屏")
        self.s4._color = "#ff5252"

    def _show_overlay(self, mode="circle"):
        if self._overlay is None:
            geo = QApplication.primaryScreen().geometry()
            self._overlay = OverlayWindow(geo, mode)
        else:
            self._overlay.mode = mode
            self._overlay.update()
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

        keyboard.add_hotkey("F6", ui._toggle_circle)
        keyboard.add_hotkey("F7", ui._toggle_zone)
        keyboard.add_hotkey("F8", lambda: ui.slider.setValue(max(0, ui.slider.value() - 5)))
        keyboard.add_hotkey("F9", lambda: ui.slider.setValue(min(100, ui.slider.value() + 5)))

        print("=" * 40)
        print("  防窥助手")
        print("=" * 40)
        print("  F6  开关防窥")
        print("  F7  降低强度")
        print("  F8  提高强度")
        print("=" * 40)
        try:
            sys.stdout.flush()
        except Exception:
            pass

        sys.exit(app.exec_())
    except Exception as e:
        try:
            print(f"[FATAL ERROR] {e}")
            traceback.print_exc()
            input("Press Enter to exit...")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()