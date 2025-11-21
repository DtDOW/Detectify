import os
import cv2 as cv
import mediapipe as mp
import numpy as np
import joblib

BASE_DIR = os.path.dirname(__file__)

PCA_PATH = os.path.join(BASE_DIR, "models", "pca_50Best.joblib")
RF_PATH = os.path.join(BASE_DIR, "models", "rf_pca50_modelBest.joblib")

# Load Models
print("Loading PCA and RF models...")
_pca = joblib.load(PCA_PATH)
_rf = joblib.load(RF_PATH)
print("Models loaded.")

facem = mp.solutions.face_mesh

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}


def extract_landmark_features(image):
    """Extract facial landmarks from a single image."""
    H, W = image.shape[:2]
    rgb = cv.cvtColor(image, cv.COLOR_BGR2RGB)

    with facem.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=False
    ) as fm:
        out = fm.process(rgb)

        if not out.multi_face_landmarks:
            return None

        pts = np.array([[p.x * W, p.y * H] for p in out.multi_face_landmarks[0].landmark])
        mean = pts.mean(axis=0)
        std = pts.std(axis=0) + 1e-6
        norm = (pts - mean) / std

        return norm.flatten()


def extract_video_features(path):
    """Extract frame-level facial landmarks."""
    video = cv.VideoCapture(path)
    if not video.isOpened():
        raise RuntimeError("Unable to open video")

    feats = []
    total_frames = int(video.get(cv.CAP_PROP_FRAME_COUNT))
    stride = max(total_frames // 30, 1)  # sample ~30 frames

    idx = 0
    with facem.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=False
    ) as fm:
        while True:
            ret, frame = video.read()
            if not ret:
                break
            if idx % stride != 0:
                idx += 1
                continue

            H, W = frame.shape[:2]
            rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            out = fm.process(rgb)

            if out.multi_face_landmarks:
                pts = np.array([[p.x * W, p.y * H] for p in out.multi_face_landmarks[0].landmark])
                mean = pts.mean(axis=0)
                std = pts.std(axis=0) + 1e-6
                feats.append(((pts - mean) / std).flatten())

            idx += 1

    video.release()
    if not feats:
        return None

    feats = np.stack(feats)
    return feats


def predict_file(path):
    """Auto-detect if image or video and run prediction."""
    ext = os.path.splitext(path)[1].lower()

    if ext in IMAGE_EXTS:
        img = cv.imread(path)
        feat = extract_landmark_features(img)
        if feat is None:
            raise RuntimeError("No face detected.")
        feats = np.array([feat])

    else:
        feats = extract_video_features(path)
        if feats is None:
            raise RuntimeError("No face detected in video.")

    mean = feats.mean(axis=0)
    std = feats.std(axis=0)
    features = np.concatenate([mean, std]).reshape(1, -1)

    x = _pca.transform(features)
    pred = _rf.predict(x)[0]
    prob = _rf.predict_proba(x)[0][pred]

    label = "REAL" if pred == 1 else "DEEPFAKE"
    return label, float(prob)

