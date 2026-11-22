# F1 Reaction Cam 🏁

F1-themed desktop app that matches webcam expressions, hand gestures and poses to your own images and videos. Driver Academy is a separate training mode. Camera frames are processed locally. Trained samples are saved as feature vectors on your Mac.

## Setup on Intel Mac

Use macOS 12 or later and Python 3.11. From the project folder:

```bash
bash install.command
bash launch.command --train
```

The installer creates an environment in `~/.venvs/f1-reaction-cam` and downloads the MediaPipe models over HTTPS. Allow your terminal app to access the camera in macOS Privacy & Security settings.

Put JPG, PNG, MP4 or MOV files in `assets/memes/` or pass `--media "/path/to/memes"`. If `~/Desktop/training/f1 meme` exists, the app uses it by default. Supply media you have permission to use.

Record your neutral expression first. Pick a meme and press Space to capture a sample. Repeat with other expressions or gestures. Close training before starting the live window:

```bash
bash launch.command
```

Saved reactions and preferences are in `data/`. To carry your training to another local copy, copy `data/` and keep the media filenames and relative paths the same.

## Checks

```bash
"$HOME/.venvs/f1-reaction-cam/bin/python" -m unittest discover -s tests -v
"$HOME/.venvs/f1-reaction-cam/bin/python" diagnose.py --camera
```

The optional playback test needs a MOV and a JPG in `assets/memes/`.

Personal media, trained samples, preferences, downloaded models and virtual environments are excluded from version control.
