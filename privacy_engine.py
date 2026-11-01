import sys

try:
    import settings_store
except ImportError:  # 单文件分发时可能没有这个模块
    settings_store = None
import os
import random
import traceback

try:
    from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QSlider, QHBoxLayout, QVBoxLayout, QDesktopWidget, QFrame, QShortcut
    from PyQt5.QtCore import Qt, QTimer, QRect, QPoint, QSize, QEvent
    from PyQt5.QtGui import QPainter, QColor, QLinearGradient, QFont, QFontMetrics, QPainterPath, QBrush, QPen, QKeySequence, QCursor
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
    def __init__(self, geo=None, mode="circle"):
        super().__init__()
        self.intensity = 0.5
        self.radius = px(150)
        self.mode = mode  # "circle" or "three_zone"

        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        # geo 可能为 None（无可用屏幕 / 远程桌面切换中）。
        # 此时不设 geometry，交给 showFullScreen 决定，避免 setGeometry(None) 抛错。
        if geo is not None:
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
        # QColor(0,0,0,alpha) 的 alpha 必须在 0..255，
        # 越界时 PyQt 会抛错或画出不可预期的结果。
        try:
            v = float(val)
        except (TypeError, ValueError):
            v = 0.5
        self.intensity = min(1.0, max(0.0, v))

    def paintEvent(self, event):
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            w, h = self.width(), self.height()

            if self.mode == "blackout":
                self._paint_blackout(p, w, h)
            elif self.mode == "three_zone":
                self._paint_three_zone(p, w, h)
            else:
                self._paint_circle(p, w, h)
        except Exception as e:
            print(f"[Overlay paint error] {e}")

    def _paint_blackout(self, p, w, h):
        """
        全屏紧急遮挡：整块屏幕压暗，中间留一行提示。

        和另外两种模式的区别：那两种是"长期开着、只遮一部分"，
        这个是"有人走过来，马上全遮住"。所以它不跟鼠标走、不留镂空，
        强度固定接近不透明，并且中心给一句提示避免用户以为死机。
        """
        # 留一点透明，让用户仍能感知到背后有东西在动，
        # 但足够挡住屏幕上的具体内容。
        alpha = int(min(1.0, max(0.0, self.intensity)) * 250)
        p.fillRect(0, 0, w, h, QColor(8, 10, 14, alpha))

        # 中央提示：全黑屏幕容易被误判为程序崩溃
        p.setPen(QColor(255, 255, 255, 40))
        p.setFont(QFont("Microsoft YaHei", max(12, int(self.width() / 40))))
        p.drawText(self.rect(), Qt.AlignCenter, "防窥中 · 按快捷键退出")

    def _paint_circle(self, p, w, h):
        """圆形可视区域模式"""
        cursor = QCursor.pos()
        # 必须减「遮罩自己」的原点，而不是主屏原点。
        # 主屏不一定是原点 (0,0)：接了副屏并把副屏设为主显示器时，
        # 主屏坐标可能是负值；遮罩也可能落在副屏上。
        # 用主屏 geometry 换算会让镂空圆圈整个偏移，用户以为防窥失效。
        g = self.geometry()
        mx = cursor.x() - g.x()
        my = cursor.y() - g.y()
        r = self.radius

        # 光标不在遮罩内（多屏、拖到另一块屏）时，不加镂空：
        # 否则圆会被画在边缘，露出一个和用户视点无关的洞。
        inside = 0 <= mx <= w and 0 <= my <= h
        if not inside:
            alpha = int(self.intensity * 255)
            p.fillRect(0, 0, w, h, QColor(0, 0, 0, alpha))
            return

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
        # 读上次的设置：强度、模式、窗口位置。
        # 防窥工具每次启动都要重拨一遍强度，用两天就烦了。
        self._settings = self._load_settings()
        self._init_ui()
        self._restore_or_center()

    def _center(self):
        f = self.frameGeometry()
        c = QDesktopWidget().availableGeometry().center()
        f.moveCenter(c)
        self.move(f.topLeft())

    # ---------- 设置持久化 ----------
    def _load_settings(self):
        if settings_store is None:
            return {"intensity": 50, "mode": "none", "window_x": None, "window_y": None}
        return settings_store.load()

    def _save_settings(self, **patch):
        """合并后落盘。失败静默：一个存不上配置的防窥工具也得能继续用。"""
        if settings_store is None:
            return
        data = dict(self._settings)
        data.update(patch)
        ok, _err = settings_store.save(data)
        if ok:
            self._settings = settings_store.load()

    def _restore_or_center(self):
        """
        有记住的位置且仍在某块屏幕可见范围内就恢复，否则居中。
        拔掉副屏后旧坐标可能落在屏幕外 —— 窗口会「启动成功但看不见」，
        对防窥工具来说比记不住位置糟糕得多。
        """
        x = self._settings.get("window_x")
        y = self._settings.get("window_y")
        if x is not None and y is not None and self._on_any_screen(x, y):
            self.move(int(x), int(y))
            return
        if x is not None:
            # 记住的位置失效了，清掉，免得每次启动都白试一次
            self._save_settings(window_x=None, window_y=None)
        self._center()

    def _on_any_screen(self, x, y):
        """窗口左上角是否落在某块屏幕内（留出能点到标题区的余量）。"""
        try:
            w = self.width() or px(420)
            h = self.height() or px(650)
            for screen in QApplication.screens():
                g = screen.availableGeometry()
                # 至少要有 120x60 的区域可见，否则用户抓不到窗口
                if (x + w > g.x() + 120 and x < g.x() + g.width() - 60
                        and y + h > g.y() + 60 and y < g.y() + g.height() - 60):
                    return True
        except Exception:
            pass
        return False

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

        hint = QLabel("F6 全屏防窥  |  F7 左右防窥  |  F8 减弱  |  F9 增强")
        self.hint = hint
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
        # 用上次保存的强度，而不是写死的 50
        saved_intensity = int(self._settings.get("intensity", 50))
        self.intensity = max(0.0, min(1.0, saved_intensity / 100.0))
        self.slider.setValue(saved_intensity)
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

        # ---- 紧急遮挡（单独一行，视觉上最突出）----
        # 放在双按钮之上是有意的：它是"来不及了"时唯一会去按的东西，
        # 位置越显眼越好。红色而非蓝色，因为它和另外两个不是同一层级。
        self.btn_blackout = QPushButton("紧急遮挡  F5")
        self.btn_blackout.setFixedHeight(px(50))
        self.btn_blackout.setCursor(Qt.PointingHandCursor)
        self.btn_blackout.setStyleSheet(
            ("QPushButton{"
             "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
             "stop:0 #c62828,stop:1 #e53935);"
             "color:white;border:none;border-radius:%dpx;"
             "font-size:%dpx;font-weight:bold;font-family:\"Microsoft YaHei\";"
             "}QPushButton:hover{background:#d32f2f;}"
             ) % (px(23), font_size(15))
        )
        self.btn_blackout.clicked.connect(self._toggle_blackout)
        lay.addWidget(self.btn_blackout)
        lay.addSpacing(px(10))

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
        foot_engine = QLabel("PRIVACY ENGINE v2.5")
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
        # 拖动过程中会连续触发。用一个单次定时器延迟落盘，
        # 松手后才真正写一次，避免每帧都碰磁盘。
        timer = getattr(self, "_save_timer", None)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self._save_settings(intensity=self.slider.value()))
            self._save_timer = timer
        timer.start(400)
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

    def _toggle_blackout(self):
        """
        紧急遮挡：整屏压暗。

        与另两种模式的关键差别是"立刻"：
        它不看鼠标位置、不做渐变、不依赖当前强度设置，
        一按就是几乎全黑。用户按这个键时通常只有一两秒反应时间。
        """
        if self.privacy_mode == "blackout":
            self.privacy_active = False
            self.privacy_mode = "none"
            self._stats_off()
            self._hide_overlay()
        else:
            self.privacy_active = True
            self.privacy_mode = "blackout"
            self._stats_on()
            # 强制高遮挡度：不跟滑块走，滑块可能是 30% 那种"轻度"。
            # 注意 _show_overlay 内部会再调一次 set_intensity，
            # 所以必须在它之后才把 intensity 改回去，
            # 否则遮罩会拿到滑块的原值，紧急遮挡变成"轻度压暗"，起不到作用。
            saved = self.intensity
            self.intensity = 0.98
            self._show_overlay("blackout")
            self._overlay.set_intensity(0.98)
            self.intensity = saved
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
        # 关闭后不再遮挡，就如实显示 0%。
        # 原来固定写 100% / 96%，用户关掉防窥后看到"遮蔽 96%"，
        # 会以为自己其实还露着 —— 这类"看着像在工作其实没工作"的显示最误导。
        self.s2.set_value("0%")
        self.s3.set_value("0%")
        self.s4.set_value("裸屏")
        self.s4._color = "#ff5252"

    def _show_overlay(self, mode="circle"):
        if self._overlay is None:
            screen = QApplication.primaryScreen()
            # 远程桌面/多屏热插拔的瞬间 primaryScreen() 可能返回 None，
            # 直接 .geometry() 会抛 AttributeError，表现为点按钮没反应。
            geo = screen.geometry() if screen is not None else None
            self._overlay = OverlayWindow(geo, mode)
        else:
            self._overlay.mode = mode
            self._overlay.update()
        self._overlay.set_intensity(self.intensity)
        # 显式指定屏幕：多屏环境下不指定时，全屏窗口可能跑到光标所在的副屏，
        # 而用户看的是主屏 —— 结果是"开了防窥"但主屏毫无遮挡。
        screen = QApplication.primaryScreen()
        if screen is not None:
            try:
                self._overlay.setScreen(screen)
            except Exception:
                pass
        self._overlay.showFullScreen()

    def _hide_overlay(self):
        if self._overlay is not None:
            self._overlay.hide()

    def closeEvent(self, event):
        # 遮罩是无父对象的顶层窗口，主窗口关闭后它不会自动消失，
        # 会一直以半透明全屏窗盖在桌面上，用户以为程序已退出却点不动桌面。
        # 这里必须显式销毁。
        try:
            if self._overlay is not None:
                timer = getattr(self._overlay, "_timer", None)
                if timer is not None:
                    timer.stop()
                self._overlay.hide()
                self._overlay.deleteLater()
                self._overlay = None
        except Exception:
            pass
        # 关窗前把当前状态记下来：下次打开直接回到上次的样子。
        # 先停掉防抖定时器，否则它可能在窗口销毁后再触发一次写盘。
        try:
            t = getattr(self, "_save_timer", None)
            if t is not None:
                t.stop()
            pos = self.pos()
            self._save_settings(
                intensity=self.slider.value(),
                mode=self.privacy_mode,
                window_x=pos.x(),
                window_y=pos.y(),
            )
        except Exception:
            pass

        self.privacy_active = False
        self.privacy_mode = "none"
        super().closeEvent(event)


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

        try:
            # F5 紧急遮挡：有人走过来时按一下，整屏立刻压暗。
            # 放在 F6 之前是因为它最急 —— 手忙脚乱时按最上面那个键最顺手。
            keyboard.add_hotkey("F5", lambda: QTimer.singleShot(0, ui._toggle_blackout))
            keyboard.add_hotkey("F6", lambda: QTimer.singleShot(0, ui._toggle_circle))
            keyboard.add_hotkey("F7", lambda: QTimer.singleShot(0, ui._toggle_zone))
            keyboard.add_hotkey("F8", lambda: QTimer.singleShot(0, lambda: ui.slider.setValue(max(0, ui.slider.value() - 5))))
            keyboard.add_hotkey("F9", lambda: QTimer.singleShot(0, lambda: ui.slider.setValue(min(100, ui.slider.value() + 5))))
        except Exception as e:
            print(f"[WARN] Hotkey registration failed (not admin?): {e}")
            try:
                # 热键失效是高频场景（非管理员 / Linux 无 /dev/input 权限），
                # 只在控制台 warn 的话用户会以为按 F6 没反应是 bug。
                ui.hint.setText("全局热键不可用（需管理员权限），请用界面按钮操作")
            except Exception:
                pass

        QShortcut(QKeySequence("F5"), ui, context=Qt.ApplicationShortcut).activated.connect(ui._toggle_blackout)
        QShortcut(QKeySequence("F6"), ui, context=Qt.ApplicationShortcut).activated.connect(ui._toggle_circle)
        QShortcut(QKeySequence("F7"), ui, context=Qt.ApplicationShortcut).activated.connect(ui._toggle_zone)
        QShortcut(QKeySequence("F8"), ui, context=Qt.ApplicationShortcut).activated.connect(lambda: ui.slider.setValue(max(0, ui.slider.value() - 5)))
        QShortcut(QKeySequence("F9"), ui, context=Qt.ApplicationShortcut).activated.connect(lambda: ui.slider.setValue(min(100, ui.slider.value() + 5)))

        print("=" * 40)
        print("  防窥助手")
        print("=" * 40)
        print("  F5  紧急遮挡（整屏压暗）")
        print("  F6  全屏圆形防窥")
        print("  F7  左右三区域防窥")
        print("  F8  强度 -5%")
        print("  F9  强度 +5%")
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