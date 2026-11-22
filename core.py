"""Camera-independent persistence, personalized matching and trigger state."""
import json
import math
import os
import time
from pathlib import Path
import numpy as np

SCHEMA = 1
EXTENSIONS = {'.jpg', '.jpeg', '.png', '.mp4', '.mov'}
NEUTRAL = '__neutral__'


def discover(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): p for p in sorted(root.rglob('*'))
            if p.is_file() and p.suffix.lower() in EXTENSIONS and not any(x.startswith('.') for x in p.relative_to(root).parts)}


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.data = {'schema': SCHEMA, 'samples': {}}
        if self.path.exists():
            self.data = json.loads(self.path.read_text())
            if self.data.get('schema') != SCHEMA:
                raise ValueError('Несовместимая версия обучения. Сохраните копию reactions.json.')
            for samples in self.data['samples'].values():
                for s in samples:
                    if len(s['mean']) != len(s['std']) or not all(math.isfinite(v) for v in s['mean'] + s['std']):
                        raise ValueError('Повреждён файл образцов')

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        with temp.open('w') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        temp.replace(self.path)

    def add(self, key, frames):
        a = np.asarray(frames, dtype=float)
        if a.ndim != 2 or len(a) < 6 or not np.isfinite(a).all():
            raise ValueError('Нужно минимум 6 корректных кадров')
        sample = {'mean': np.median(a, axis=0).tolist(), 'std': np.std(a, axis=0).tolist(), 'frames': len(a)}
        self.data['samples'].setdefault(key, []).append(sample)
        self.save()

    def delete(self, key, index=None):
        if index is None:
            self.data['samples'].pop(key, None)
        elif key in self.data['samples']:
            self.data['samples'][key].pop(index)
        self.save()


class Matcher:
    """Class-specific discriminative weights; rejection by distance and margin.

    Scores are similarity, NOT calibrated probabilities. Neutral is a real class.
    """
    def __init__(self, store, keys=None, threshold=.30, margin=.045):
        self.store, self.keys = store, keys
        self.threshold, self.margin = threshold, margin

    def predict(self, vector):
        x = np.asarray(vector, dtype=float)
        classes = {k: v for k, v in self.store.data['samples'].items()
                   if v and (k == NEUTRAL or self.keys is None or k in self.keys)}
        classes = {k: v for k, v in classes.items() if all(len(s['mean']) == len(x) for s in v)}
        if not classes or not np.isfinite(x).all():
            return None, 0., 'Нет образцов'
        centers = {k: np.median([s['mean'] for s in v], axis=0) for k, v in classes.items()}
        scores = []
        for k, samples in classes.items():
            others = [c for n, c in centers.items() if n != k]
            contrast = np.min(np.abs(np.asarray(others) - centers[k]), axis=0) if others else np.ones_like(x)*.1
            weights = .02 + np.minimum(contrast / .12, 3.)
            distances = []
            for s in samples:
                # Variance tolerance is bounded so noisy recordings cannot match everything.
                scale = .10 + np.clip(np.asarray(s['std']), 0, .10)
                d = np.abs(x - s['mean']) / scale
                distances.append(float(np.sqrt(np.average(np.minimum(d, 10.)**2, weights=weights))))
            scores.append((min(distances), k))
        scores.sort()
        distance, key = scores[0]
        similarity = math.exp(-distance)
        if similarity < self.threshold:
            return None, similarity, 'Нет похожей реакции'
        if len(scores) > 1 and math.exp(-scores[1][0]) > similarity - self.margin:
            return None, similarity, 'Похожие реакции — уточните обучение'
        if key == NEUTRAL:
            return None, similarity, 'Нейтральное выражение'
        if NEUTRAL not in classes:
            return None, similarity, 'Сначала запишите нейтральное выражение'
        return key, similarity, 'Реакция'


class Trigger:
    def __init__(self, dwell=.45, release=.7, cooldown=1.5, hold=1.5):
        self.dwell, self.release, self.cooldown, self.hold = dwell, release, cooldown, hold
        self.reset()

    def reset(self):
        self.candidate = self.active = None
        self.since = self.last_fire = self.empty_since = None
        self.armed = True

    def update(self, key, now=None):
        now = time.monotonic() if now is None else now
        if key is None:
            self.candidate, self.since = None, None
            if self.empty_since is None:
                self.empty_since = now
            if now - self.empty_since >= self.release:
                self.armed = True
            return None
        self.empty_since = None
        if key != self.candidate:
            self.candidate, self.since = key, now
        if now - self.since < self.dwell:
            return None
        if self.last_fire is not None and now - self.last_fire < max(self.cooldown, self.hold):
            return None
        if key == self.active and not self.armed:
            return None
        self.active, self.last_fire, self.armed = key, now, False
        return key
