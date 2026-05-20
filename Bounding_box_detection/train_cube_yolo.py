# ===============================
# File: train_cube_yolo.py
# ===============================
"""
YOLOv8 training script for cube detection
----------------------------------------
Purpose
    - Train a YOLOv8 model on a custom cube dataset defined by ``data.yaml``.
    - Validate the trained model and run a quick prediction on a random test image.
    - Display the saved annotated prediction with matplotlib.

Notes
    - The training outputs go to ``runs/train/<RUN_NAME>``.
    - The prediction outputs go to ``runs/predict/predict*/<image>.jpg``.
"""

# ===============================
# File: train_cube_yolo.py
# ===============================
"""
YOLOv8 training script for cube detection (fine-tune friendly)
"""
import os
import random
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from ultralytics import YOLO
from pathlib import Path
import sys 

_root = Path(__file__).resolve().parent
for _ in range(6):  # goes up to 6 levels if needed
    if (_root / "paths.py").exists():
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        break
    _root = _root.parent
# --------------------------------------------------------------------------
from paths import PROJECT_ROOT, PYTHON_EXE as VENV_PYTHON, ensure_dobot_importable
ensure_dobot_importable()

# ===== Config & paths =====
DATA_YAML_PATH = os.path.join("Bounding_box_detection", "dataset", "data.yaml")
# If an old best exists, we start from it; otherwise, we start from yolov8n.pt
OLD_BEST = os.path.join("runs", "train", "cube_yolo", "weights", "best.pt")
MODEL_WEIGHTS = OLD_BEST if os.path.exists(OLD_BEST) else "yolov8n.pt"

EPOCHS = 50
IMAGE_SIZE = 640
RUN_NAME = "cube_yolo_v2"          # new run folder for this iteration
PROJECT_DIR = "runs/train"

# Choose a test image; if empty, we take a validation image
TEST_IMAGE_DIR = os.path.join("cube_detection", "dataset", "test", "images")
VALID_IMAGE_DIR = os.path.join("cube_detection", "dataset", "valid", "images")
def _pick_any_image(folder):
    if not os.path.isdir(folder):
        return None
    imgs = [f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".png", ".jpeg"))]
    return os.path.join(folder, random.choice(imgs)) if imgs else None

TEST_IMAGE = _pick_any_image(TEST_IMAGE_DIR) or _pick_any_image(VALID_IMAGE_DIR)

# ===== Helpers =====
def train_model(weights: str, data_yaml: str, epochs: int, imgsz: int, run_name: str) -> YOLO:
    """
    Load a YOLO model (from previous best or yolov8n) and train on the dataset.
    """
    print(f"🔧 Using weights: {weights}")
    print(f"📄 Using data.yaml: {data_yaml}")
    model = YOLO(weights)
    model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        project=PROJECT_DIR,
        name=run_name,
        exist_ok=True,      # reuse/complete the file if prompted again
        # device=0,         # uncomment if you want to force GPU 0; otherwise auto
        # batch=16,         # adjust if you want
    )
    return model

def evaluate_model(model: YOLO):
    metrics = model.val()
    print("\n📊 Evaluation finished. Metrics:")
    print(metrics)
    return metrics

def predict_and_show(model: YOLO, image_path: str) -> None:
    results = model.predict(source=image_path, save=True, save_txt=True, conf=0.3)
    saved_image_path = os.path.join(results[0].save_dir, os.path.basename(image_path))
    img = mpimg.imread(saved_image_path)
    plt.figure(figsize=(8, 8))
    plt.imshow(img)
    plt.title("YOLOv8 prediction result")
    plt.axis("off")
    plt.show()

# ===== Runtime =====
if __name__ == "__main__":
    if not os.path.exists(DATA_YAML_PATH):
        raise FileNotFoundError(f"data.yaml not found at: {DATA_YAML_PATH}")

    yolo = train_model(MODEL_WEIGHTS, DATA_YAML_PATH, EPOCHS, IMAGE_SIZE, RUN_NAME)
    evaluate_model(yolo)

    if TEST_IMAGE:
        print(f"🖼️ Quick check on: {TEST_IMAGE}")
        predict_and_show(yolo, TEST_IMAGE)
    else:
        print("⚠️ No image found in test/ or valid/ for quick visualization.")
