"""Optional real Qt playback integration. No camera needed."""
import os
import unittest
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtMultimedia import QMediaPlayer
    from media_player import MediaPane
    QT = True
except ImportError:
    QT = False

@unittest.skipUnless(QT,'PySide6 не установлен')
class PlaybackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def wait(self,ms):
        loop = QEventLoop()
        QTimer.singleShot(ms,loop.quit)
        loop.exec()

    def test_video_image_switch_and_audio_controls(self):
        root = Path(__file__).resolve().parents[1]/'assets'/'memes'
        video = next(root.glob('*.mov'),None)
        image = next(root.glob('*.JPG'),None)
        if not video or not image:
            self.skipTest('Нет bundled media')
        errors = []
        pane = MediaPane(errors.append)
        pane.show_file(video)
        for _ in range(100):
            self.wait(100)
            if pane.player.hasVideo() or errors:
                break
        self.assertFalse(errors,errors)
        self.assertTrue(pane.player.hasVideo(),'Qt не декодировал MOV за 10 секунд')
        self.assertIs(pane.player.audioOutput(),pane.audio)
        pane.audio.setMuted(True)
        pane.audio.setVolume(.4)
        self.assertTrue(pane.audio.isMuted())
        self.assertAlmostEqual(pane.audio.volume(),.4,places=5)
        pane.show_file(image)
        self.assertEqual(pane.player.playbackState(),QMediaPlayer.StoppedState)
        self.assertTrue(pane.player.source().isEmpty())
        self.assertIs(pane.layout.currentWidget(),pane.image)
        pane.show_file(video)
        self.assertEqual(pane.current,video)
        pane.stop()
        pane.close()
