import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description="F1 Reaction Cam")
    p.add_argument("--train", action="store_true")
    local_media = Path.home() / "Desktop" / "training" / "f1 meme"
    p.add_argument(
        "--media",
        type=Path,
        default=local_media if local_media.is_dir() else ROOT / "assets" / "memes",
    )
    p.add_argument("--camera", type=int, default=0)
    args = p.parse_args()
    if sys.version_info[:2] != (3, 11):
        print("Используйте Python 3.11.", file=sys.stderr)
        return 1
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        import os
        import PySide6
        from PySide6.QtCore import QCoreApplication

        plugins = Path(PySide6.__file__).resolve().parent / "Qt" / "plugins"
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugins / "platforms")
        QCoreApplication.setLibraryPaths([str(plugins)])
        import subprocess

        subprocess.run(["chflags", "-R", "nohidden", str(plugins)], check=True)
        import subprocess

        subprocess.run(["chflags", "-R", "nohidden", str(plugins)], check=True)
        app = QApplication(sys.argv)
        app.setApplicationName("F1 Reaction Cam")
        from main_window import MainWindow

        window = MainWindow(ROOT, args)
        window.show()
        return app.exec()
    except Exception as e:
        print(f"Не удалось запустить: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
