from ultralytics import YOLO
import os
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import random

# === 0. Paramètres ===
DATA_YAML_PATH = os.path.join("Keypoint_detection", "dataset","images", "data.yaml")
MODEL_NAME = "yolov8n-seg.pt"  # ⚠️ modèle pour segmentation
EPOCHS = 50
IMAGE_SIZE = 640
RUN_NAME = "cube_yolo_seg"
SAVE_DIR = os.path.join("runs", "train", RUN_NAME)

test_image_dir = os.path.join("Keypoint_detection", "dataset", "test","images")
print("le chemin :",test_image_dir)
all_images = [f for f in os.listdir(test_image_dir) if f.endswith(('.jpg', '.png'))]
random_image = random.choice(all_images)
TEST_IMAGE = os.path.join(test_image_dir, random_image)
print(TEST_IMAGE)

# === 1. Charger le modèle YOLOv8-seg pré-entraîné ===
model = YOLO(MODEL_NAME)

# === 2. Entraînement ===
model.train(
    data=DATA_YAML_PATH,
    epochs=EPOCHS,
    imgsz=IMAGE_SIZE,
    task="segment",             # ➕ important : segmentation
    batch=2,                    # 👈 Ajoute ici
    project="runs/train",
    name=RUN_NAME,
    exist_ok=True
)


# === 3. Évaluation ===
metrics = model.val()
print("\n📊 Évaluation terminée. Résultats :")
print(metrics)

# === 4. Prédiction ===
results = model.predict(
    source=TEST_IMAGE,
    save=True,
    save_txt=True,
    conf=0.3,
    task="segment"             # ➕ important aussi ici
)

# === 5. Visualisation avec matplotlib ===
saved_image_path = os.path.join(results[0].save_dir, os.path.basename(TEST_IMAGE))

img = mpimg.imread(saved_image_path)
plt.figure(figsize=(8, 8))
plt.imshow(img)
plt.title("Résultat de la prédiction YOLOv8-Seg")
plt.axis("off")
plt.show()
