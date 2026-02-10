from pathlib import Path

import cv2 # type: ignore
import numpy as np # type: ignore

from backend.config import (
    BLUR_THRESHOLD,
    BRIGHTNESS_MAX,
    BRIGHTNESS_MIN,
    FACE_CENTER_MAX_OFFSET_RATIO,
    MAX_FACES,
    MIN_FACE_SIZE,
    MODEL_PATH,
)

# Use Haar cascade for face detection (simple + offline)
CASCADE_PATH = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
FACE_CASCADE = cv2.CascadeClassifier(str(CASCADE_PATH))

def load_lbph():
    if not MODEL_PATH.exists():
        return None
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(str(MODEL_PATH))
    return recognizer

RECOGNIZER = load_lbph()

def recognize_from_frame(frame_bgr, threshold=70.0):
    """
    Returns:
      (teacher_id:int|None, confidence:float|None, reason:str|None)
    """
    global RECOGNIZER
    if RECOGNIZER is None:
        RECOGNIZER = load_lbph()
        if RECOGNIZER is None:
            return None, None, "model_missing"

    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80))

    if len(faces) == 0:
        return None, None, "no_face"

    if MAX_FACES > 0 and len(faces) > MAX_FACES:
        return None, None, "multiple_faces"

    # take largest face
    x, y, w, h = sorted(faces, key=lambda r: r[2]*r[3], reverse=True)[0]

    if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
        return None, None, "face_too_small"

    frame_h, frame_w = gray.shape
    face_cx = x + (w / 2.0)
    face_cy = y + (h / 2.0)
    frame_cx = frame_w / 2.0
    frame_cy = frame_h / 2.0
    max_offset = FACE_CENTER_MAX_OFFSET_RATIO * min(frame_w, frame_h)
    if max_offset > 0:
        dist = ((face_cx - frame_cx) ** 2 + (face_cy - frame_cy) ** 2) ** 0.5
        if dist > max_offset:
            return None, None, "face_off_center"

    face = gray[y:y+h, x:x+w]
    face = cv2.resize(face, (200, 200))

    mean_brightness = float(face.mean())
    if mean_brightness < BRIGHTNESS_MIN:
        return None, None, "too_dark"
    if mean_brightness > BRIGHTNESS_MAX:
        return None, None, "too_bright"

    blur_score = float(cv2.Laplacian(face, cv2.CV_64F).var())
    if blur_score < BLUR_THRESHOLD:
        return None, None, "too_blurry"

    label, conf = RECOGNIZER.predict(face)
    # LBPH: lower confidence = better match
    if conf <= threshold:
        return int(label), float(conf), None

    return None, float(conf), "no_match"

def reload_model():
    global RECOGNIZER
    RECOGNIZER = load_lbph()
    return RECOGNIZER is not None
