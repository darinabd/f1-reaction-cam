import threading
import time
from pathlib import Path
import cv2
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
from detector import Detector


class Camera(QThread):
    frame = Signal(QImage)
    feature = Signal(object)
    status = Signal(str)

    def __init__(self, model_dir, index=0):
        super().__init__()
        self.model_dir, self.index = model_dir, index
        self.stop_event = threading.Event()
        self.ack = threading.Event()
        self.ack.set()

    def run(self):
        cap = detector = None
        try:
            self.status.emit('Загрузка моделей…')
            detector = Detector(self.model_dir)
            cap = cv2.VideoCapture(self.index, cv2.CAP_AVFOUNDATION)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
            cap.set(cv2.CAP_PROP_FPS,30)
            if not cap.isOpened():
                raise RuntimeError('Камера недоступна. Разрешите доступ в macOS → Конфиденциальность → Камера.')
            self.status.emit('● LIVE')
            last_analysis = 0
            errors = 0
            while not self.stop_event.is_set():
                ok, frame = cap.read()
                if not ok:
                    errors += 1
                    if errors > 15:
                        raise RuntimeError('Камера перестала отдавать кадры')
                    self.msleep(30)
                    continue
                errors = 0
                rgb = cv2.cvtColor(cv2.flip(frame,1), cv2.COLOR_BGR2RGB)
                # At most one display frame in Qt queue; inference never blocks the GUI.
                if self.ack.is_set():
                    self.ack.clear()
                    self.frame.emit(QImage(rgb.data,rgb.shape[1],rgb.shape[0],rgb.strides[0],QImage.Format_RGB888).copy())
                now = time.monotonic()
                if now-last_analysis >= .09:
                    last_analysis = now
                    self.feature.emit(detector.extract(rgb,int(now*1000)))
        except Exception as e:
            self.status.emit(f'Ошибка: {e}')
        finally:
            if cap is not None:
                cap.release()
            if detector is not None:
                detector.close()

    def stop(self):
        self.stop_event.set()
