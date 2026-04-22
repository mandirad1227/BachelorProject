from ultralytics import YOLO
import os
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import random
import cv2
import numpy as np
import json

# === Paramètres ===
BASE_DIR = "Keypoint_detection/dataset"
DATA_YAML_PATH = os.path.join(BASE_DIR, "data.yaml")
MODEL_NAME = "yolov8n-pose.pt"  # modèle de keypoints
EPOCHS = 50
IMAGE_SIZE = 640
RUN_NAME = "cube_keypoints"
SAVE_DIR = os.path.join("runs", "train", RUN_NAME)

# === Choix aléatoire d'une image test ===
test_image_dir = os.path.join(BASE_DIR, "test", "images")
all_images = [f for f in os.listdir(test_image_dir) if f.endswith(('.jpg', '.png'))]
random_image = random.choice(all_images)
TEST_IMAGE = os.path.join(test_image_dir, random_image)

# === 1. Charger le modèle ===
model = YOLO(MODEL_NAME)

# === 2. Entraînement ===
model.train(
    data=DATA_YAML_PATH,
    epochs=EPOCHS,
    imgsz=IMAGE_SIZE,
    project="runs/train",
    name=RUN_NAME,
    exist_ok=True
)

# === 3. Évaluation ===
metrics = model.val()
print("\n Evaluation terminee. resultats :")
print(metrics)

# === 4. Prédiction ===
results = model.predict(
    source=TEST_IMAGE,
    save=True,
    save_txt=True,
    conf=0.05
)

# === 5. Visualisation avec le centre (moyenne des 8 points) ===
pred_image_path = os.path.join(results[0].save_dir, os.path.basename(TEST_IMAGE))
img = cv2.imread(pred_image_path)

for result in results:
    for keypoints in result.keypoints.xy:
        if keypoints.shape[0] == 8:
            coords = keypoints.numpy()
            xs = coords[:, 0]
            ys = coords[:, 1]
            x_center = int(xs.mean())
            y_center = int(ys.mean())
            cv2.circle(img, (x_center, y_center), 6, (0, 255, 255), -1)  # Jaune
            for (x, y) in zip(xs, ys):
                cv2.circle(img, (int(x), int(y)), 4, (0, 0, 255), -1)


# === Enregistrement des centres détectés ===
output_data = {"centers": []}

for result in results:
    for keypoints in result.keypoints.xy:
        if keypoints.shape[0] == 8:
            coords = keypoints.numpy()
            x_center = float(np.mean(coords[:, 0]))
            y_center = float(np.mean(coords[:, 1]))
            output_data["centers"].append({
                "x": round(x_center, 2),
                "y": round(y_center, 2)
            })

# === Sauvegarde dans un fichier JSON ===
json_output_path = os.path.join(BASE_DIR, "results_centers.json")
with open(json_output_path, "w") as f:
    json.dump(output_data, f, indent=2)

print(f"✅ Coordonnées des centres sauvegardées dans : {json_output_path}")


img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
plt.figure(figsize=(8, 8))
plt.imshow(img_rgb)
plt.title("Keypoints + centre (jaune)")
plt.axis("off")
plt.show()
