from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtWidgets import QWidget, QStackedLayout
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget


class ImageView(QWidget):
    def __init__(self):
        super().__init__()
        self.pixmap = QPixmap()
        self.setMinimumSize(240,240)

    def setPixmap(self, pixmap):
        self.pixmap = pixmap
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), Qt.black)
        if not self.pixmap.isNull():
            fitted = self.pixmap.scaled(self.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation)
            p.drawPixmap((self.width()-fitted.width())//2,(self.height()-fitted.height())//2,fitted)


class MediaPane(QWidget):
    def __init__(self, error_callback):
        super().__init__()
        self.layout = QStackedLayout(self)
        self.image = ImageView()
        self.video = QVideoWidget()
        self.video.setAspectRatioMode(Qt.KeepAspectRatio)
        self.layout.addWidget(self.image)
        self.layout.addWidget(self.video)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(.7)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.errorOccurred.connect(lambda error,text:error_callback('Ошибка видео: '+text))
        self.current = None

    def show_file(self, path):
        self.player.stop()
        self.player.setSource(QUrl())
        self.current = path
        if path.suffix.lower() in {'.mp4','.mov'}:
            self.layout.setCurrentWidget(self.video)
            self.player.setSource(QUrl.fromLocalFile(str(path.resolve())))
            self.player.play()
        else:
            from PIL import Image, ImageOps
            from PySide6.QtGui import QImage
            with Image.open(path) as source:
                picture = ImageOps.exif_transpose(source).convert("RGBA")
                raw = picture.tobytes()
                image = QImage(
                    raw, picture.width, picture.height,
                    picture.width * 4, QImage.Format_RGBA8888
                ).copy()
            pixmap = QPixmap.fromImage(image)
            if pixmap.isNull():
                raise ValueError(f'Не удалось прочитать изображение: {path.name}')
            self.image.setPixmap(pixmap)
            self.layout.setCurrentWidget(self.image)

    def replay(self):
        if self.current:
            self.show_file(self.current)

    def stop(self):
        self.player.stop()
