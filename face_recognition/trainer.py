import cv2
import numpy as np

from backend.config import FACES_DIR, MODEL_PATH

DATASET_DIR = FACES_DIR
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
FACE_CASCADE = cv2.CascadeClassifier(CASCADE_PATH)


def train_model():
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    faces = []
    labels = []

    if not DATASET_DIR.exists():
        print("[train] No dataset folder found.")
        return False

    for teacher_dir in DATASET_DIR.iterdir():
        if not teacher_dir.is_dir():
            continue

        try:
            label = int(teacher_dir.name)
        except ValueError:
            continue

        for img_path in teacher_dir.iterdir():
            if not img_path.is_file():
                continue

            img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue

            faces_detected = FACE_CASCADE.detectMultiScale(
                img,
                scaleFactor=1.2,
                minNeighbors=5,
                minSize=(80, 80),
            )
            if len(faces_detected) == 0:
                continue

            x, y, w, h = sorted(
                faces_detected,
                key=lambda r: r[2] * r[3],
                reverse=True,
            )[0]
            face = img[y : y + h, x : x + w]
            face = cv2.resize(face, (200, 200))

            faces.append(face)
            labels.append(label)

    if len(faces) == 0:
        print("[train] No valid faces found. Training aborted.")
        return False

    recognizer.train(faces, np.array(labels))
    recognizer.save(str(MODEL_PATH))
    print("[train] Face model trained successfully.")
    return True


if __name__ == "__main__":
    train_model()
