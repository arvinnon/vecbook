import cv2
import os
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "assets", "faces")
MODEL_PATH = os.path.join(BASE_DIR, "face_recognition", "face_model.yml")

CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
FACE_CASCADE = cv2.CascadeClassifier(CASCADE_PATH)

def train_model():
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    faces = []
    labels = []

    if not os.path.exists(DATASET_DIR):
        print("❌ No dataset folder found.")
        return False

    for teacher_id in os.listdir(DATASET_DIR):
        folder = os.path.join(DATASET_DIR, teacher_id)
        if not os.path.isdir(folder):
            continue

        try:
            label = int(teacher_id)
        except ValueError:
            continue

        for img_name in os.listdir(folder):
            img_path = os.path.join(folder, img_name)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue

            faces_detected = FACE_CASCADE.detectMultiScale(
                img, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80)
            )
            if len(faces_detected) == 0:
                continue

            x, y, w, h = sorted(faces_detected, key=lambda r: r[2]*r[3], reverse=True)[0]
            face = img[y:y+h, x:x+w]
            face = cv2.resize(face, (200, 200))

            faces.append(face)
            labels.append(label)

    if len(faces) == 0:
        print("❌ No valid faces found. Training aborted.")
        return False

    recognizer.train(faces, np.array(labels))
    recognizer.save(MODEL_PATH)
    print("✅ Face model trained successfully")
    return True

if __name__ == "__main__":
    train_model()

print("🔁 Training started in background...")
