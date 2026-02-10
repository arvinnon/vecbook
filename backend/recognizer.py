import os
import cv2 # type: ignore
import numpy as np # type: ignore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "face_recognition", "face_model.yml")

# Use Haar cascade for face detection (simple + offline)
CASCADE_PATH = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
FACE_CASCADE = cv2.CascadeClassifier(CASCADE_PATH)

def load_lbph():
    if not os.path.exists(MODEL_PATH):
        return None
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(MODEL_PATH)
    return recognizer

RECOGNIZER = load_lbph()

def recognize_from_frame(frame_bgr, threshold=70.0):
    """
    Returns:
      (teacher_id:int|None, confidence:float|None)
    """
    global RECOGNIZER
    if RECOGNIZER is None:
        RECOGNIZER = load_lbph()
        if RECOGNIZER is None:
            return None, None

    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80))

    if len(faces) == 0:
        return None, None

    # take largest face
    x, y, w, h = sorted(faces, key=lambda r: r[2]*r[3], reverse=True)[0]
    face = gray[y:y+h, x:x+w]
    face = cv2.resize(face, (200, 200))

    label, conf = RECOGNIZER.predict(face)
    # LBPH: lower confidence = better match
    if conf <= threshold:
        return int(label), float(conf)

    return None, float(conf)

def reload_model():
    global RECOGNIZER
    RECOGNIZER = load_lbph()
    return RECOGNIZER is not None