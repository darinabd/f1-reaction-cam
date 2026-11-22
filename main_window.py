import time
import json
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QSplitter,
    QSlider,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QMessageBox,
)
from core import Store, Matcher, Trigger, discover, NEUTRAL
from camera import Camera
from media_player import MediaPane, ImageView

STYLE = """
QWidget {background:#121317;color:#f4f4f6;font-family:"Helvetica Neue";font-size:13px;}
QLabel#title {font-size:28px;font-weight:800;}
QLabel#section {color:#fa3b43;font-size:12px;font-weight:700;}
QPushButton {background:#282b33;border:1px solid #363a45;border-radius:7px;padding:9px;}
QPushButton:hover {background:#414550;} QPushButton:checked {background:#bf1825;}
QPushButton:disabled {color:#666;} QListWidget {background:#1b1d24;border:0;border-radius:8px;}
QListWidget::item {padding:8px;} QListWidget::item:selected {background:#8c1723;}
QSlider::groove:horizontal {height:4px;background:#444;} QSlider::handle:horizontal {background:#f33240;width:14px;margin:-5px 0;}
"""


TEAM_COLORS = (
    ("FERRARI", "#ed303b"),
    ("McLAREN", "#ff8d28"),
    ("RED BULL", "#5676ff"),
    ("MERCEDES", "#47dbca"),
    ("ALPINE", "#ff71b4"),
    ("ASTON MARTIN", "#24aa82"),
    ("HAAS", "#e2e5ed"),
    ("AUDI", "#ff4775"),
    ("WILLIAMS", "#43b8ff"),
    ("CADILLAC", "#d6b16b"),
    ("RED BULL VISA", "#a0aaff"),
)


class RaceBanner(QWidget):
    """Draw an F1-inspired wordmark, race cars and the finish flag."""

    def __init__(self, training):
        super().__init__()
        self.training = training
        self.setFixedHeight(170)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#1b1c22"))
        painter.fillRect(0, 0, 6, self.height(), QColor("#f13431"))
        painter.setPen(QColor("#ff514b"))
        painter.setFont(QFont("Helvetica Neue", 24, QFont.Bold, italic=True))
        painter.drawText(22, 48, "F1")
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Helvetica Neue", 23, QFont.Bold))
        painter.drawText(86, 48, "DRIVER ACADEMY" if self.training else "REACTION CAM")
        painter.setPen(QColor("#bbc0cc"))
        painter.setFont(QFont("Helvetica Neue", 12))
        painter.drawText(
            24, 77, "ТРЕНИРОВКА РЕАКЦИЙ" if self.training else "ПРЯМОЙ ЭФИР"
        )
        painter.setFont(QFont("Helvetica Neue", 10, QFont.Bold))
        x, y = 24, 107
        for name, color in TEAM_COLORS:
            width = painter.fontMetrics().horizontalAdvance(name) + 26
            if x + width > self.width() - 20 and x > 24:
                x, y = 24, y + 22
            painter.fillRect(x, y - 8, 8, 8, QColor(color))
            painter.setPen(QColor(color))
            painter.drawText(x + 13, y, name)
            x += width
        if self.width() < 680:
            return
        for row in range(5):
            for col in range(5):
                color = "#f1f2f4" if (row + col) % 2 == 0 else "#383b46"
                painter.fillRect(
                    self.width() - 75 + col * 11, 31 + row * 11, 11, 11, QColor(color)
                )
        for index, color in enumerate(color for _, color in TEAM_COLORS[:4]):
            x, y = self.width() - 205 - (index % 2) * 113, 30 + (index // 2) * 47
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#111217"))
            for dx in (12, 61):
                for dy in (0, 20):
                    painter.drawRoundedRect(x + dx, y + dy, 18, 11, 3, 3)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(x + 17, y + 9, 76, 13, 5, 5)
            painter.drawRoundedRect(x + 34, y + 5, 31, 21, 5, 5)
            painter.drawRect(x + 5, y + 3, 10, 25)
            painter.drawRect(x + 85, y + 5, 9, 21)
            painter.setBrush(QColor("#101116"))
            painter.drawEllipse(x + 45, y + 10, 14, 11)


class MainWindow(QMainWindow):
    def __init__(self, root, args):
        super().__init__()
        self.root, self.args = root, args
        self.store = Store(root / "data" / "reactions.json")
        settings_path = root / "data" / "settings.json"
        try:
            self.settings = (
                json.loads(settings_path.read_text()) if settings_path.exists() else {}
            )
        except (ValueError, OSError):
            self.settings = {}
        self.files = discover(args.media)
        self.matcher = Matcher(self.store, self.files)
        self.matcher.threshold = float(self.settings.get("threshold", 0.30))
        self.trigger = Trigger()
        self.recording = None
        self.frames = []
        self.record_start = 0
        self.record_deadline = 0
        self.running = not args.train
        self.worker = None
        self.closing = False
        self.setWindowTitle("F1 Driver Academy" if args.train else "F1 Reaction Cam")
        self.resize(1280, 820)
        self.setStyleSheet(STYLE)
        body = QWidget()
        self.setCentralWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(RaceBanner(args.train))
        self.notice = QLabel(
            "Выбери мем и нажми Space для записи образца."
            if args.train
            else "M — звук   ·   F — полный экран"
        )
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        split = QSplitter(Qt.Horizontal)
        layout.addWidget(split, 1)
        sidebar = QWidget()
        side = QVBoxLayout(sidebar)
        self.auto_next = QCheckBox("После записи — следующий мем")
        self.auto_next.setChecked(True)
        side.addWidget(self.auto_next)
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.select)
        side.addWidget(self.list, 1)
        self.sample_list = QListWidget()
        self.sample_list.setMaximumHeight(100)
        side.addWidget(self.sample_list)
        for text, callback in [
            ("▶ Просмотреть / повторить", self.preview),
            ("● Записать образец [Space]", self.capture),
            ("○ Записать нейтральное", lambda: self.capture(NEUTRAL)),
            ("Далее / пропустить", self.next),
            ("Удалить выбранный образец", self.remove_sample),
            ("Сбросить выбранную реакцию", self.remove_class),
            ("Обновить список файлов", self.refresh),
        ]:
            button = QPushButton(text)
            button.clicked.connect(lambda checked=False, fn=callback: fn())
            side.addWidget(button)
        split.addWidget(sidebar)
        sidebar.setVisible(args.train)
        panels = QWidget()
        panel_layout = QHBoxLayout(panels)
        left = QVBoxLayout()
        right = QVBoxLayout()
        for column, text in ((left, "LIVE CAMERA"), (right, "F1 REACTION")):
            label = QLabel(text)
            label.setObjectName("section")
            column.addWidget(label)
        self.camera_view = ImageView()
        left.addWidget(self.camera_view, 1)
        self.live = QLabel("Камера запускается…")
        left.addWidget(self.live)
        self.match_label = QLabel("Ожидание реакции")
        self.match_label.setWordWrap(True)
        left.addWidget(self.match_label)
        self.media = MediaPane(self.message)
        right.addWidget(self.media, 1)
        self.filename = QLabel(
            "Выбери мем для просмотра" if args.train else "Ожидание реакции"
        )
        self.filename.setWordWrap(True)
        right.addWidget(self.filename)
        panel_layout.addLayout(left, 1)
        panel_layout.addLayout(right, 1)
        split.addWidget(panels)
        split.setSizes([270, 1000])
        controls = QHBoxLayout()
        self.start = QPushButton(
            "Остановить распознавание" if self.running else "Начать распознавание"
        )
        self.start.clicked.connect(self.toggle_running)
        controls.addWidget(self.start)
        self.start.setVisible(not args.train)
        self.mute = QCheckBox("Без звука [M]")
        self.mute.toggled.connect(self.media.audio.setMuted)
        self.mute.setChecked(bool(self.settings.get("muted", False)))
        controls.addWidget(self.mute)
        volume = QSlider(Qt.Horizontal)
        volume.setRange(0, 100)
        volume.setValue(int(self.settings.get("volume", 70)))
        self.media.audio.setVolume(volume.value() / 100)
        volume.setMaximumWidth(120)
        volume.valueChanged.connect(lambda v: self.media.audio.setVolume(v / 100))
        controls.addWidget(volume)
        controls.addWidget(QLabel("Камера:"))
        self.camera_index = QSpinBox()
        self.camera_index.setRange(0, 10)
        self.camera_index.setValue(args.camera)
        controls.addWidget(self.camera_index)
        restart = QPushButton("Подключить")
        restart.clicked.connect(self.restart_camera)
        controls.addWidget(restart)
        controls.addWidget(QLabel("Порог сходства:"))
        threshold = QDoubleSpinBox()
        threshold.setRange(0.15, 0.95)
        threshold.setSingleStep(0.05)
        threshold.setValue(self.matcher.threshold)
        threshold.valueChanged.connect(lambda v: setattr(self.matcher, "threshold", v))
        controls.addWidget(threshold)
        fullscreen = QPushButton("Полный экран [F]")
        fullscreen.clicked.connect(self.fullscreen)
        controls.addWidget(fullscreen)
        layout.addLayout(controls)
        self.shortcuts = []
        shortcuts = [
            ("M", lambda: self.mute.setChecked(not self.mute.isChecked())),
            ("F", self.fullscreen),
            ("Escape", self.showNormal),
        ]
        if args.train:
            shortcuts.append(("Space", self.capture))
        for key, callback in shortcuts:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)
        self.populate()
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.check_recording)
        self.timer.start()
        QTimer.singleShot(0, self.launch_camera)
        if not self.files:
            self.message(f"Мемы не найдены: {args.media}. Укажите папку через --media.")

    def message(self, text):
        self.notice.setText(text)

    def populate(self, selected=None):
        self.list.blockSignals(True)
        self.list.clear()
        self.keys = [NEUTRAL] + list(self.files)
        for key in self.keys:
            n = len(self.store.data["samples"].get(key, []))
            label = "Нейтральное выражение" if key == NEUTRAL else key
            self.list.addItem(f"{label}  ·  {n} записей")
        self.list.blockSignals(False)
        if self.keys:
            self.list.setCurrentRow(
                self.keys.index(selected) if selected in self.keys else 0
            )
        self.update_samples()

    def selected(self):
        row = self.list.currentRow()
        return self.keys[row] if 0 <= row < len(self.keys) else None

    def select(self, row):
        self.update_samples()
        if self.args.train:
            self.preview()

    def update_samples(self):
        self.sample_list.clear()
        for i, s in enumerate(self.store.data["samples"].get(self.selected(), [])):
            self.sample_list.addItem(f'Образец {i+1} · {s["frames"]} кадров')

    def preview(self):
        key = self.selected()
        if key and key in self.files:
            try:
                self.media.show_file(self.files[key])
                self.filename.setText(key)
                if self.running:
                    self.running = False
                    self.update_start()
                    self.trigger.reset()
            except Exception as e:
                self.message(str(e))

    def next(self):
        if self.recording:
            return
        self.list.setCurrentRow((self.list.currentRow() + 1) % max(1, len(self.keys)))
        if not self.args.train:
            self.preview()

    def refresh(self):
        self.files = discover(self.args.media)
        self.matcher.keys = self.files
        self.populate(self.selected())
        self.trigger.reset()

    def update_start(self):
        self.start.setText(
            "Остановить распознавание" if self.running else "Начать распознавание"
        )

    def toggle_running(self):
        if self.recording:
            self.message("Дождитесь окончания записи")
            return
        self.running = not self.running
        if not self.running:
            self.media.stop()
        self.trigger.reset()
        self.update_start()

    def capture(self, key=None):
        if self.recording:
            return
        if not self.worker or not self.worker.isRunning():
            self.message("Сначала подключите камеру")
            return
        key = key or self.selected()
        if not key:
            return
        self.running = False
        self.update_start()
        self.trigger.reset()
        self.recording = key
        self.frames = []
        self.record_start = time.monotonic() + 2
        self.record_deadline = self.record_start + 3
        self.message(
            "Приготовьтесь: запись через 2 секунды. Удерживайте выражение / жест."
        )

    def check_recording(self):
        if not self.recording:
            return
        now = time.monotonic()
        if now < self.record_start:
            self.message(f"Приготовьтесь… {self.record_start-now:.1f} с")
        elif now < self.record_deadline:
            self.message(
                f"● ЗАПИСЬ {self.record_deadline-now:.1f} с · {len(self.frames)} кадров"
            )
        else:
            key, self.recording = self.recording, None
            try:
                self.store.add(key, self.frames)
                self.populate(self.selected())
                n = len(self.store.data["samples"][key])
                self.message(
                    f"Сохранено: {key}, запись {n}. Добавьте 2–3 записи с небольшими изменениями положения; Далее — следующий мем."
                )
                if self.auto_next.isChecked():
                    self.next()
            except Exception as e:
                self.message(
                    "Запись не сохранена: "
                    + str(e)
                    + ". Лицо должно быть видно. Повторите Space."
                )

    def remove_sample(self):
        key, index = self.selected(), self.sample_list.currentRow()
        if key and index >= 0 and not self.recording:
            self.store.delete(key, index)
            self.populate(key)
            self.trigger.reset()

    def remove_class(self):
        key = self.selected()
        if (
            key
            and not self.recording
            and QMessageBox.question(
                self, "Переобучение", f"Удалить все образцы только для {key}?"
            )
            == QMessageBox.Yes
        ):
            self.store.delete(key)
            self.populate(key)
            self.trigger.reset()

    def launch_camera(self):
        if self.closing:
            return
        if self.worker and self.worker.isRunning():
            return
        missing = [
            n
            for n in (
                "face_landmarker.task",
                "gesture_recognizer.task",
                "pose_landmarker_lite.task",
            )
            if not (self.root / "models" / n).exists()
        ]
        if missing:
            self.live.setText(
                "Нет моделей. Выполните python setup_models.py и нажмите Подключить."
            )
            return
        self.worker = Camera(self.root / "models", self.camera_index.value())
        self.worker.frame.connect(self.show_frame)
        self.worker.feature.connect(self.on_feature)
        self.worker.status.connect(self.live.setText)
        self.worker.start()

    def restart_camera(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.finished.connect(self.launch_camera)
        else:
            self.launch_camera()

    def show_frame(self, image):
        self.camera_view.setPixmap(QPixmap.fromImage(image))
        if self.worker:
            self.worker.ack.set()

    def on_feature(self, vector):
        if self.recording:
            if (
                self.record_start <= time.monotonic() < self.record_deadline
                and vector is not None
            ):
                self.frames.append(vector.tolist())
            return
        if not self.running:
            return
        if vector is None:
            key, score, reason = None, 0.0, "Человек не обнаружен"
        else:
            key, score, reason = self.matcher.predict(vector)
        self.match_label.setText(f"{key or reason} · сходство {score:.0%}")
        fired = self.trigger.update(key)
        if fired and fired in self.files:
            try:
                self.media.show_file(self.files[fired])
                self.filename.setText(fired)
            except Exception as e:
                self.message(str(e))

    def fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def closeEvent(self, event):
        self.closing = True
        self.timer.stop()
        self.media.stop()
        if self.worker and self.worker.isRunning():
            event.ignore()
            self.worker.stop()
            self.worker.finished.connect(self.close)
            self.message("Освобождение камеры…")
        else:
            settings = {
                "threshold": self.matcher.threshold,
                "volume": round(self.media.audio.volume() * 100),
                "muted": self.mute.isChecked(),
            }
            try:
                target = self.root / "data" / "settings.json"
                target.parent.mkdir(exist_ok=True)
                temp = target.with_suffix(".tmp")
                temp.write_text(json.dumps(settings, indent=2))
                temp.replace(target)
            except OSError as e:
                print("Не удалось сохранить настройки:", e)
            event.accept()
