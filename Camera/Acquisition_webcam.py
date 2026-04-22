# ===============================
# File: Acquisition_webcam.py
# ===============================
"""
Interactive webcam snapshot tool
--------------------------------
Purpose
    - Open a webcam stream and let the user capture still images by pressing SPACE.
    - Overlay a counter (current/maximum) on the preview.
    - Save captured frames into a dataset folder; exit with ESC or when the quota is reached.

Notes
    - Uses OpenCV's HighGUI windows; requires a local display.
    - Camera can now be selected by **name** using DirectShow enumeration (pygrabber),
      which is more reliable than raw numeric indices when they change between runs.
"""

import os
import cv2

# DirectShow enumeration (to resolve camera name -> stable index)
try:
    from pygrabber.dshow_graph import FilterGraph
except Exception:
    FilterGraph = None

# ===============================
#      Configuration & State
# ===============================
SAVE_DIR = "Keypoint_detection/dataset/test/images"
CAMERA_DEVICE = 0  # e.g. "C505e HD Webcam" or "Logi C270 HD WebCam" or an int index
MAX_IMAGES = 15


# ===============================
#          Function defs
# ===============================

def list_cameras_dshow() -> list[str]:
    """Return DirectShow camera names in OS order (empty list if not available)."""
    if not FilterGraph:
        return []
    try:
        return FilterGraph().get_input_devices()
    except Exception:
        return []


def resolve_index_by_name(name: str) -> int | None:
    """
    Map a camera friendly name (substring, case-insensitive) to its DirectShow index.
    Returns None if not found.
    """
    devices = list_cameras_dshow()
    name_l = name.lower()
    for i, dev in enumerate(devices):
        if name_l in dev.lower():
            return i
    return None


def open_camera_by_name(name: str) -> cv2.VideoCapture:
    """
    Open a camera by friendly name by first resolving to a DSHOW index,
    then opening by index (tries CAP_DSHOW then CAP_MSMF).
    """
    idx = resolve_index_by_name(name)
    if idx is None:
        raise RuntimeError(f"Camera '{name}' not found. Available: {list_cameras_dshow()}")

    for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF):
        cap = cv2.VideoCapture(idx, backend)
        if cap.isOpened():
            return cap

    raise RuntimeError(f"Could not open camera '{name}' at resolved index {idx} using DSHOW/MSMF.")


def init_camera(device=CAMERA_DEVICE) -> cv2.VideoCapture:
    """
    Wrapper to open the configured camera.
    - If 'device' is a str: open by name (DSHOW enumerate -> index -> open).
    - If 'device' is an int: open by numeric index (DSHOW then MSMF).
    """
    if isinstance(device, str):
        return open_camera_by_name(device)

    # Fallback: open by numeric index
    for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF, 0):
        cap = cv2.VideoCapture(int(device), backend) if backend != 0 else cv2.VideoCapture(int(device))
        if cap.isOpened():
            return cap
    raise RuntimeError(f"Error: cannot open webcam index: {device}")


def capture_and_save(
    cap: cv2.VideoCapture,
    save_dir: str,
    max_images: int = 15,
    start_index: int = 1,
) -> None:
    """Interactive loop: SPACE to capture, ESC to quit.

    Each capture is saved as ``capture_{i}.jpg`` in ``save_dir``.
    """
    os.makedirs(save_dir, exist_ok=True)
    print("Press SPACE to capture an image, ESC to quit.")

    count = 0
    while count < max_images:
        ret, frame = cap.read()
        if not ret:
            print("Error while grabbing a frame.")
            break

        display = frame.copy()
        cv2.putText(
            display,
            f"Image {count + start_index}/{max_images}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )

        cv2.imshow("Capture", display)
        key = cv2.waitKey(1) & 0xFF

        if key == 27:  # ESC
            break
        if key == 32:  # SPACE
            filename = f"capture_{count + start_index}.jpg"
            path = os.path.join(save_dir, filename)
            cv2.imwrite(path, frame)
            print(f"📸 Saved: {path}")
            count += 1

    cap.release()
    cv2.destroyAllWindows()
    print("✅ Capture finished.")


# ===============================
#              Runtime
# ===============================
if __name__ == "__main__":
    cam = init_camera(CAMERA_DEVICE)  # <- use the name here
    capture_and_save(cam, SAVE_DIR, MAX_IMAGES)
