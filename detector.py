"""Single owner of all MediaPipe tasks; fixed, versioned feature layout."""
from contextlib import ExitStack
from pathlib import Path
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class Detector:
    def __init__(self, model_dir):
        self.stack = ExitStack()
        base = lambda name: python.BaseOptions(model_asset_path=str(Path(model_dir)/name))
        try:
            self.face = self.stack.enter_context(vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
                base_options=base('face_landmarker.task'), running_mode=vision.RunningMode.VIDEO,
                output_face_blendshapes=True, output_facial_transformation_matrixes=True, num_faces=1)))
            self.hands = self.stack.enter_context(vision.GestureRecognizer.create_from_options(vision.GestureRecognizerOptions(
                base_options=base('gesture_recognizer.task'), running_mode=vision.RunningMode.VIDEO, num_hands=2)))
            self.pose = self.stack.enter_context(vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
                base_options=base('pose_landmarker_lite.task'), running_mode=vision.RunningMode.VIDEO, num_poses=1)))
        except Exception:
            self.stack.close()
            raise
        self.hand_result = self.pose_result = None
        self.counter = 0

    def extract(self, rgb, timestamp):
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        face = self.face.detect_for_video(image, timestamp)
        # Face every analysis frame; hands/pose every other frame.
        if self.counter % 2 == 0:
            self.hand_result = self.hands.recognize_for_video(image, timestamp)
            self.pose_result = self.pose.detect_for_video(image, timestamp)
        self.counter += 1
        if face.face_landmarks:
            fl = face.face_landmarks[0]
            center = np.array([fl[1].x, fl[1].y])
            face_scale = max(np.linalg.norm(np.array([fl[234].x-fl[454].x, fl[234].y-fl[454].y])), .05)
            features = [1.] + [c.score for c in sorted(face.face_blendshapes[0], key=lambda c:c.category_name)]
            # Rotation matrix carries head direction without absolute camera position.
            features.extend((np.asarray(face.facial_transformation_matrixes[0])[:3,:3].ravel()*.5).tolist())
        else:
            # Facepalm may occlude the face. Keep hands/pose, mark face absent.
            if not self.hand_result.hand_landmarks and not self.pose_result.pose_landmarks:
                return None
            center = np.array([.5,.35])
            face_scale = .2
            if self.pose_result.pose_landmarks:
                p = self.pose_result.pose_landmarks[0]
                center = np.array([p[0].x,p[0].y])
                face_scale = max(abs(p[11].x-p[12].x)*.6,.08)
            features = [0.]*62
        slots = {}
        hr = self.hand_result
        for i, landmarks in enumerate(hr.hand_landmarks):
            side = hr.handedness[i][0].category_name
            if side in slots:
                continue
            points = np.array([[p.x,p.y,p.z] for p in landmarks])
            wrist = points[0]
            scale = max(np.linalg.norm(points[9]-wrist), .025)
            local = np.clip((points-wrist)/scale, -3,3)/3
            relative = np.clip((wrist[:2]-center)/face_scale, -3,3)/3
            slots[side] = [1., *relative, *local.ravel()]
        for side in ('Left','Right'):
            features.extend(slots.get(side, [0.]*66))
        pr = self.pose_result
        if pr.pose_landmarks:
            p = pr.pose_landmarks[0]
            shoulder = np.array([(p[11].x+p[12].x)/2,(p[11].y+p[12].y)/2])
            scale = max(np.linalg.norm(np.array([p[11].x-p[12].x,p[11].y-p[12].y])), .08)
            for i in (11,12,13,14,15,16,23,24):
                visible = float(p[i].visibility > .6)
                xy = np.clip((np.array([p[i].x,p[i].y])-shoulder)/scale,-3,3)/3 if visible else [0.,0.]
                features.extend([visible,*xy])
        else:
            features.extend([0.]*24)
        return np.asarray(features, dtype=np.float32)

    def close(self):
        self.stack.close()
