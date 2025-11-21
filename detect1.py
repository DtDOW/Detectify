# detect.py
import os
import cv2 as cv
import mediapipe as mp
import numpy as np
import joblib

# === MODEL PATHS ===
BASE_DIR = os.path.dirname(__file__)
PCA_PATH = os.path.join(BASE_DIR, "models", "pca_50Best.joblib")
RF_PATH = os.path.join(BASE_DIR, "models", "rf_pca50_modelBest.joblib")

# === VIDEO SETTINGS ===
SAMPLE_FPS = 1
MAX_FACES = 5
MIN_DET_CONF = 0.5
MIN_TRK_CONF = 0.5

# === INIT MEDIAPIPE ===
facem = mp.solutions.face_mesh

def landmarks_features(landmarks, H, W):
    pts = np.array([[p.x * W, p.y * H] for p in landmarks], dtype=np.float32)
    mean = pts.mean(axis=0, keepdims=True)
    std = pts.std(axis=0, keepdims=True) + 1e-6
    norm = (pts - mean) / std
    return norm.flatten()

def extract_frames_features(video_path, sample_fps=SAMPLE_FPS):
    video = cv.VideoCapture(video_path)
    if not video.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    feats = []
    native_fps = video.get(cv.CAP_PROP_FPS) or 30.0
    stride = max(int(round(native_fps / max(sample_fps, 1e-6))), 1)

    with facem.FaceMesh(
        static_image_mode=False,
        max_num_faces=MAX_FACES,
        refine_landmarks=False,
        min_detection_confidence=MIN_DET_CONF,
        min_tracking_confidence=MIN_TRK_CONF
    ) as fm:
        frame_idx = 0
        while True:
            ret, frame = video.read()
            if not ret:
                break
            if frame_idx % stride != 0:
                frame_idx += 1
                continue

            H, W, _ = frame.shape
            frame_rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            out = fm.process(frame_rgb)

            if out.multi_face_landmarks:
                j = out.multi_face_landmarks[0]
                feat = landmarks_features(j.landmark, H, W)
                feats.append(feat)

            frame_idx += 1

    video.release()
    if not feats:
        return None
    return np.stack(feats, axis=0)

# -------- Load models once at import time --------
print("Loading PCA and RF models...")
_pca = joblib.load(PCA_PATH)
_rf = joblib.load(RF_PATH)
print("Models loaded.")

def predict_video_file(video_path):
    """
    Returns (label: "REAL"/"DEEPFAKE", prob: float) or raises RuntimeError
    """
    feats = extract_frames_features(video_path)
    if feats is None:
        raise RuntimeError("No face detected in the video.")

    mean = feats.mean(axis=0)
    std = feats.std(axis=0)
    agg = np.concatenate([mean, std]).reshape(1, -1)

    X_reduced = _pca.transform(agg)
    pred = _rf.predict(X_reduced)[0]
    prob = _rf.predict_proba(X_reduced)[0][pred]

    label = "REAL" if pred == 1 else "DEEPFAKE"
    return label, float(prob)
