import cv2
import numpy as np

def detect_red_corners(image_path, debug=False):
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image not found at: {image_path}")

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Red mask (handle HSV wraparound)
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)

    # Denoise
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    red_corners = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 10 < area < 500:
            M = cv2.moments(cnt)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                red_corners.append((cx, cy))

    if len(red_corners) != 4:
        raise ValueError(f"❌ Found {len(red_corners)} red points, 4 required.")

    # === Tri personnalisé selon ta photo ===
    red_corners_sorted = sorted(red_corners, key=lambda p: p[1])
    top_two = sorted(red_corners_sorted[:2], key=lambda p: p[0])     # top-left, top-right
    bottom_two = sorted(red_corners_sorted[2:], key=lambda p: p[0])  # bottom-left, bottom-right

    # Order: bottom-left, top-left, top-right, bottom-right
    ordered = [bottom_two[0], top_two[0], top_two[1], bottom_two[1]]

    if debug:
        debug_image = image.copy()
        for i, (x, y) in enumerate(ordered):
            cv2.circle(debug_image, (x, y), 10, (255, 0, 255), -1)
            cv2.putText(debug_image, str(i+1), (x+10, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
        cv2.imshow("Detected Corners", debug_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return ordered


# Example usage:
if __name__ == "__main__":
    path = r"C:\Users\TOUJAN Oceam\Documents\CentraleSupelec\Voyage Norvege\Work\Keypoint_detection\dataset\test\images\capture_1.jpg"  # Adjust if needed
    corners = detect_red_corners(path, debug=True)
    print("Detected corners:", corners)
