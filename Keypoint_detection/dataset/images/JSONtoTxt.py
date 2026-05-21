import os
import json
import cv2

# === CONFIGURATION ===

json_folder = os.path.join("Keypoint_detection","dataset","images","train")
output_labels_folder = os.path.join("Keypoint_detection","dataset","images","label_test")
image_folder = os.path.join("Keypoint_detection","dataset","images","train")
class_name = "Cube"  # peut être généralisé

# Associe une classe à un ID
class_id_map = {class_name: 0}

os.makedirs(output_labels_folder, exist_ok=True)

for filename in os.listdir(json_folder):
    if filename.endswith(".json"):
        json_path = os.path.join(json_folder, filename)
        with open(json_path, 'r') as f:
            data = json.load(f)

        image_path = os.path.join(image_folder, data["imagePath"])
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ Image introuvable : {image_path}")
            continue
        h, w = image.shape[:2]

        output_txt_path = os.path.join(output_labels_folder, filename.replace(".json", ".txt"))
        with open(output_txt_path, 'w') as out_file:
            for shape in data["shapes"]:
                label = shape["label"]
                points = shape["points"]
                cls_id = class_id_map.get(label, 0)

                normalized = []
                for x, y in points:
                    normalized.append(f"{x / w:.6f}")
                    normalized.append(f"{y / h:.6f}")
                out_file.write(f"{cls_id} " + " ".join(normalized) + "\n")

print("✅ Conversion terminée.")
