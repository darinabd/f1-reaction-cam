"""Verified TLS, atomic downloads, reuses valid local task archives."""
import argparse
import shutil
import ssl
import urllib.request
import zipfile
from pathlib import Path
import certifi

MODELS = {
 'face_landmarker.task':'face_landmarker/face_landmarker/float16/1/face_landmarker.task',
 'gesture_recognizer.task':'gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task',
 'pose_landmarker_lite.task':'pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task',
}

def valid(path):
    return path.exists() and zipfile.is_zipfile(path) and path.stat().st_size > 100000


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reuse',type=Path,help='Папка с уже загруженными моделями')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent/'models'
    root.mkdir(exist_ok=True)
    context = ssl.create_default_context(cafile=certifi.where())
    for name,url in MODELS.items():
        target = root/name
        if valid(target):
            print('Готово:',name)
            continue
        temp = target.with_suffix('.download')
        try:
            if args.reuse and valid(args.reuse/name):
                shutil.copy2(args.reuse/name,temp)
            else:
                print('Загрузка:',name,flush=True)
                with urllib.request.urlopen('https://storage.googleapis.com/mediapipe-models/'+url,context=context,timeout=90) as r, temp.open('wb') as out:
                    shutil.copyfileobj(r,out)
            if not valid(temp):
                raise RuntimeError('Сервер вернул некорректную модель')
            temp.replace(target)
        finally:
            temp.unlink(missing_ok=True)

if __name__ == '__main__':
    main()
