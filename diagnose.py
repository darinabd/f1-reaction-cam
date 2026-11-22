"""Opt-in hardware/media checks: python diagnose.py --camera --media 'path.mov'."""
import argparse
import platform
import sys
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--camera',action='store_true')
    p.add_argument('--index',type=int,default=0)
    p.add_argument('--media',type=Path)
    args = p.parse_args()
    import cv2, numpy, mediapipe, PySide6
    print(platform.platform(),platform.machine(),sys.version)
    print('OpenCV',cv2.__version__,'NumPy',numpy.__version__,'MediaPipe',mediapipe.__version__,'Qt',PySide6.__version__)
    from detector import Detector
    detector = Detector(Path(__file__).parent/'models')
    try:
        import numpy as np
        print('Models: loaded; blank-frame inference:',detector.extract(np.zeros((480,640,3),dtype=np.uint8),1))
    finally:
        detector.close()
    if args.camera:
        cap = cv2.VideoCapture(args.index,cv2.CAP_AVFOUNDATION)
        try:
            ok,frame = cap.read()
            print('Camera:',ok, None if not ok else frame.shape)
            if not ok:
                raise RuntimeError('Нет кадров камеры')
        finally:
            cap.release()
    if args.media:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtMultimedia import QMediaDevices
        from media_player import MediaPane
        app = QApplication([])
        print('Audio outputs:',[d.description() for d in QMediaDevices.audioOutputs()])
        pane = MediaPane(print)
        pane.resize(800,600)
        pane.show()
        pane.show_file(args.media)
        print('Проверьте картинку и оригинальный звук. Закройте окно после проверки.')
        app.exec()

if __name__ == '__main__':
    main()
