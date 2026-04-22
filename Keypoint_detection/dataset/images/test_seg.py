import cv2
import numpy as np
import json
from ultralytics import YOLO
import os
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import json
import shutil

BASE_DIR = r"C:\Users\TOUJAN Oceam\Documents\CentraleSupelec\Voyage Norvege\Work"

Nom_Img = os.path.join("imgTest6.jpg")

def Find_cubes_seg(Nom_Img):
    """
    🔍 Detects cubes on a given image using a trained YOLOv8 segmentation model.
    Extracts the center of each mask, saves them in a JSON file, and displays the image.

    Args:
        Nom_Img (str): Filename of the image to analyze.

    Returns:
        None. Saves 'positions.json' and shows the annotated image.
    """
    import numpy as np

    # === Charger le modèle YOLOv8 SEGMENTATION ===
    model_path = os.path.join(BASE_DIR, "runs", "train", "cube_yolo_seg", "weights", "best.pt")
    model = YOLO(model_path)

    # === Charger l'image cible ===
    TEST_IMAGE = os.path.join(r"C:\Users\TOUJAN Oceam\Documents\CentraleSupelec\Voyage Norvege\Work\Keypoint_detection\dataset\test\images",Nom_Img)

    # === Lancer la prédiction ===
    results = model.predict(
        source=TEST_IMAGE,
        save=True,
        save_txt=True,
        conf=0.2,
        project="results",
        name=f"analyse_{Nom_Img}"
    )

    components = []

    # === Extraire les centres à partir des masques ===
    count = 0
    components = []

    for r in results:
        if r.masks is not None:
            masks = r.masks.data.cpu().numpy()  # (N, H, W)
            count = masks.shape[0]
            print(f"✅ {count} masques détectés")

            for i in range(count):
                mask = masks[i]
                ys, xs = np.where(mask > 0.5)

                if len(xs) > 0 and len(ys) > 0:
                    x_center = int(np.mean(xs))
                    y_center = int(np.mean(ys))
                    components.append({
                        "x": x_center,
                        "y": y_center,
                        "z": -60,
                        "rail": 575
                    })

        else:
            print("❌ Aucun masque détecté dans cette image.")

    # === Affichage du résultat avec les centres marqués ===
    print(f"j'ai {count} cubes detectés")
    saved_image_path = os.path.join(BASE_DIR, "results", f"analyse_{Nom_Img}", Nom_Img)


    img = mpimg.imread(saved_image_path)

    plt.figure(figsize=(8, 8))
    plt.imshow(img)
    plt.title(f"Centres détectés sur {Nom_Img}")
    plt.axis("off")

    # Ajout des points rouges sur les centres
    for comp in components:
        plt.plot(comp["x"], comp["y"], "ro")

    plt.show()

Find_cubes_seg(Nom_Img)