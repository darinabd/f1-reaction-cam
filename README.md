<div align="center">

# 🏁 F1 Reaction Cam

**Your expression. Your gesture. Your race-day reaction.**

`Python 3.11` · `MediaPipe` · `OpenCV` · `PySide6` · `Intel macOS`

[Features](#features) · [Quick start](#quick-start) · [Under the hood](#under-the-hood) · [Checks](#checks)

</div>

---

An F1-themed desktop app that turns webcam expressions, hand gestures, and poses into your own reaction clips. Teach it a reaction in **Driver Academy**, then see it play back in the **Live Cam**.

## Features

| Mode | What you can do |
| --- | --- |
| **Driver Academy** | Pair a face expression, hand gesture, or pose with a meme and record training samples. |
| **Live Cam** | See your camera and the matched reaction side by side. Play images or video clips with adjustable sound. |

Camera frames are processed locally. Saved samples contain numeric features for matching reactions.

## Quick start

**Requirements** · Intel Mac, macOS 12 or later, Python 3.11, and a webcam.

1. **Install.** From the project folder, run:
   ```bash
   bash install.command
   ```
   This installs dependencies in `~/.venvs/f1-reaction-cam` and downloads the MediaPipe models over HTTPS. Allow your terminal app to access the camera under **Privacy & Security → Camera** on macOS.

2. **Add media.** Place JPG, PNG, MP4, or MOV files you have permission to use in `assets/memes/`. If `~/Desktop/training/f1 meme` exists, it takes priority. Use `--media "/path/to/memes"` with either launch mode to choose a different folder.

3. **Train.** Open **Driver Academy**, record a neutral expression, then select a meme and press **Space** to capture a sample. Repeat for your other reactions.
   ```bash
   bash launch.command --train
   ```

4. **Go live.** Close Driver Academy and launch the live window.
   ```bash
   bash launch.command
   ```

## Under the hood

| Component | What it handles |
| --- | --- |
| **OpenCV** | Webcam capture |
| **MediaPipe** | Face, hand, and pose features |
| **NumPy** | Matching live features against saved samples |
| **PySide6** | Desktop UI and media playback |

Reactions and preferences live in `data/`. To transfer your training to another local copy, copy `data/` and preserve the media filenames and relative paths. The repository excludes personal media, training data, preferences, downloaded models, and virtual environments.

## Checks

```bash
"$HOME/.venvs/f1-reaction-cam/bin/python" -m unittest discover -s tests -v
"$HOME/.venvs/f1-reaction-cam/bin/python" diagnose.py --camera
```

The optional playback test uses a MOV and a JPG from `assets/memes/`.

---

<p align="center"><sub>Unofficial Formula 1 fan project.</sub></p>
