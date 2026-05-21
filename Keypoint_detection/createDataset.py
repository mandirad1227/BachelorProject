import cv2
import os

# === Paths ===
IMAGE_FOLDER = "Keypoint_detection/dataset/images/train"
LABEL_FOLDER = "Keypoint_detection/dataset/labels/train"

os.makedirs(LABEL_FOLDER, exist_ok=True)

# === Globals ===
current_image = None
image_name = ""
image_index = 0
all_images = [f for f in os.listdir(IMAGE_FOLDER) if f.lower().endswith((".jpg", ".png"))]
annotations = []
current_keypoints = []

def mouse_callback(event, x, y, flags, param):
    global current_image, current_keypoints
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(current_keypoints) < 8:
            current_keypoints.append((x, y, 2))
            cv2.circle(current_image, (x, y), 5, (0, 0, 255), -1)
            cv2.putText(current_image, str(len(current_keypoints)-1), (x+5, y-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            cv2.imshow("Annotation", current_image)
    elif event == cv2.EVENT_RBUTTONDOWN:
        if len(current_keypoints) < 8:
            current_keypoints.append((x, y, 1))
            cv2.circle(current_image, (x, y), 5, (0, 0, 0), -1)
            cv2.putText(current_image, str(len(current_keypoints)-1), (x+5, y-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.imshow("Annotation", current_image)

def save_yolo_keypoints(label_path, img_shape, all_annotations):
    h, w = img_shape[:2]
    with open(label_path, "w") as f:
        for keypoints in all_annotations:
            if len(keypoints) != 8:
                continue
            keypoints_str = ""
            for (x, y, v) in keypoints:
                x_norm = x / w
                y_norm = y / h
                keypoints_str += f"{x_norm:.6f} {y_norm:.6f} {v} "
            line = f"0 0.5 0.5 1 1 {keypoints_str.strip()}\n"
            f.write(line)

def annotate_image(image_path):
    global current_image, image_name, current_keypoints, annotations
    image_name = os.path.basename(image_path)
    current_image = cv2.imread(image_path)
    clone = current_image.copy()
    annotations = []
    current_keypoints = []
    cv2.imshow("Annotation", current_image)
    cv2.setMouseCallback("Annotation", mouse_callback)

    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == ord("r"):
            current_keypoints = []
            current_image = clone.copy()
            for kp in annotations:
                for i, (x, y, v) in enumerate(kp):
                    color = (0, 0, 255) if v == 2 else (0, 0, 0)
                    cv2.circle(current_image, (int(x), int(y)), 5, color, -1)
                    cv2.putText(current_image, str(i), (int(x)+5, int(y)-5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            cv2.imshow("Annotation", current_image)
        elif key == ord("n") and len(current_keypoints) == 8:
            annotations.append(current_keypoints.copy())
            current_keypoints = []
            current_image = clone.copy()
            for kp in annotations:
                for i, (x, y, v) in enumerate(kp):
                    color = (0, 0, 255) if v == 2 else (0, 0, 0)
                    cv2.circle(current_image, (int(x), int(y)), 5, color, -1)
                    cv2.putText(current_image, str(i), (int(x)+5, int(y)-5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            cv2.imshow("Annotation", current_image)
            print("Objet ajoute.")
        elif key == ord("s"):
            label_path = os.path.join(LABEL_FOLDER, image_name.replace(".jpg", ".txt").replace(".png", ".txt"))
            save_yolo_keypoints(label_path, current_image.shape, annotations)
            print(f"Fichier sauvegarde dans : {label_path}")
            break
        elif key == ord("q"):
            print("Image ignoree.")
            break

    cv2.destroyAllWindows()

def run_tool():
    global image_index
    while image_index < len(all_images):
        img_path = os.path.join(IMAGE_FOLDER, all_images[image_index])
        print(f"\nTraitement : {all_images[image_index]}")
        annotate_image(img_path)
        image_index += 1

run_tool()
