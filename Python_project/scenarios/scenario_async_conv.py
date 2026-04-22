"""
Asynchronous scenario for the conveyor Dobot (vision + color sorting)
--------------------------------------------------------------------
Purpose
    Control a Dobot Magician working with a belt/linear motion and an IR gate.
    When the IR sensor triggers, the conveyor stops, a snapshot is taken,
    a cube is detected with YOLOv8, its (x, y) is projected to robot coordinates
    via a homography computed from 4 red calibration dots, the robot picks the cube,
    moves to a color sensor to read RGB, classifies it as "radioactive" or not
    based on persisted thresholds, and sorts it to the corresponding drop zone.

High‑level pipeline
    1) Initialize Dobot DLL + connect to the conveyor Dobot; enable sensors (IR + color).
    2) Initialize the camera.
    3) On IR trigger: stop the conveyor motor.
    4) Capture an image, detect 4 red dots → compute homography H (first pass only).
    5) Run YOLOv8, take the first detected bounding box → center (x, y).
    6) Apply homography → (x_loc, y_loc) in robot frame; pick at a safe Z.
    7) Move to the color sensor, read RGB → decide bin; place accordingly, then resume.

Notes / prerequisites
    - Windows with the Dobot SDK available (DobotDllType.py + DobotDll.dll) and importable.
    - Paths are machine‑specific; adjust constants below to your environment.
    - CTRL_BREAK (Windows) / SIGTERM/SIGINT triggers an emergency stop that disconnects cleanly.
    - Logic is preserved from the original script; wording and structure were improved only.
"""

# ===============================
#              Imports
# ===============================
import os
import sys
import time
import signal
import ctypes
import shutil
import json
import cv2
import numpy as np
import matplotlib.pyplot as plt  # kept for optional debug display
import matplotlib.image as mpimg  # kept for optional debug display
import requests
from ultralytics import YOLO
from flask import current_app  # may not be used at runtime, kept for parity
from pathlib import Path
_root = Path(__file__).resolve().parent
for _ in range(6):  # remonte jusqu'à 6 niveaux si besoin
    if (_root / "paths.py").exists():
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        break
    _root = _root.parent
# --------------------------------------------------------------------------

from paths import PROJECT_ROOT, PYTHON_EXE as VENV_PYTHON, ensure_dobot_importable
ensure_dobot_importable()

# Ensure we can import project-level modules (get_port.py, launcher.py) from a subfolder
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import DobotDllType as dType  # after sys.path injection
from get_port import get_port
from launcher import dobot_emergency_stop


# ===============================
#          Function defs
# ===============================

def handle_sigterm(signum, frame):
    """
    Signal handler (emergency stop): stop motors, release the camera, suction OFF,
    disconnect from the Dobot DLL, then exit the process.

    Note: the handler relies on the globals ``api_conv`` and ``cap`` initialized at runtime.
    """
    print("🛑 SIGBREAK/SIGTERM received, emergency stop for Dobot Conveyor")
    if api_conv:
        try:
            dType.SetEMotorEx(api_conv, 1, 0, int(0), 1)
            dType.SetEMotorEx(api_conv, 0, 0, int(0), 1)
            try :
                cap.release()
            except Exception as e :
                print(e)
            dobot_emergency_stop(api_conv)
            dType.DisconnectDobot(api_conv)
        except Exception as e:
            print(f"⚠️ Error during emergency stop: {e}")
            try:
                dType.DisconnectDobot(api_conv)
            except Exception:
                pass
    sys.exit(0)


# ---------- Camera utilities ----------

sys.path.insert(0, str(PROJECT_ROOT / "Camera"))
from Acquisition_webcam import open_camera_by_name, list_cameras_dshow


def take_snapshot(device_name: str,
                  save_path: str,
                  width: int | None = None,
                  height: int | None = None,
                  warmup: int = 3) -> str:
    """
    Open the camera by name, grab ONE frame, save it, then close.

    Args:
        device_name: e.g. "C505e HD Webcam" or "Logi C270 HD WebCam"
        save_path:   output image path
        width/height: optional requested resolution
        warmup:      number of throwaway frames to stabilize exposure

    Returns:
        save_path
    """
    cap = open_camera_by_name(device_name)
    try:
        if width is not None:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        if height is not None:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        # Warm-up to avoid first black frames
        for _ in range(warmup):
            cap.read()
            time.sleep(0.03)

        ok, frame = cap.read()
        if not ok or frame is None:
            raise RuntimeError("Failed to grab a frame from camera.")

        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        cv2.imwrite(save_path, frame)
        print("pic save at :", save_path)
        return save_path
    finally:
        cap.release()



# ---------- Vision: YOLO + homography + red dots ----------

def Find_cubes(image_path: str):
    """
    Detect cubes using YOLOv8 and return their centers.

    Args:
        image_path: Full path to the image.

    Returns:
        list[dict]: Each dict has keys {"x", "y", "z"}.
    """
    # Load the trained YOLOv8 model (prefer new run, fallback to old)
    v2_weights = os.path.join(BASE_DIR, "runs", "train", "cube_yolo_v2", "weights", "best.pt")
    v1_weights = os.path.join(BASE_DIR, "runs", "train", "cube_yolo",    "weights", "best.pt")
    if os.path.isfile(v2_weights):
        model_path = v2_weights
    elif os.path.isfile(v1_weights):
        model_path = v1_weights
    else:
        raise FileNotFoundError(
            f"No trained weights found at:\n- {v2_weights}\n- {v1_weights}"
        )
    model = YOLO(model_path)

    # Prepare output folder names
    image_filename = os.path.basename(image_path)
    analyse_name = f"analyse_{os.path.splitext(image_filename)[0]}"
    analyse_folder = os.path.join(BASE_DIR, "results", analyse_name)

    if os.path.exists(analyse_folder):
        print(f"🗑️ Folder {analyse_folder} found. Deleting…")
        shutil.rmtree(analyse_folder)
    else:
        print(f"✅ No existing folder {analyse_folder}, ready for analysis.")

    # YOLO prediction
    results = model.predict(
        source=image_path,
        save=True,
        save_txt=True,
        conf=0.05,
        project=str(Path(BASE_DIR) / "results"),
        name=analyse_name,
    )

    # Build the list of components (bounding box centers)
    components = []
    for r in results:
        for box in r.boxes.xyxy:
            x1, y1, x2, y2 = box.tolist()
            x_center = int((x1 + x2) / 2)
            y_center = int((y1 + y2) / 2)
            components.append({"x": x_center, "y": y_center, "z": -60})

    print(f"✅ Detected {len(components)} component(s).")

    # Copy the annotated image to the web interface static folder
    saved_image_path = os.path.join(BASE_DIR, "results", analyse_name, image_filename)
    dest_folder = str(PROJECT_ROOT / "Interface" / "static" / "dossier2")
    os.makedirs(dest_folder, exist_ok=True)
    dest_path = os.path.join(dest_folder, os.path.basename(saved_image_path))
    shutil.copy2(saved_image_path, dest_path)

    # Optional debug view (kept commented)
    # img = mpimg.imread(saved_image_path)
    # plt.figure(figsize=(8, 8))
    # plt.imshow(img)
    # plt.axis("off")
    # for comp in components:
    #     plt.plot(comp["x"], comp["y"], "ro")
    # plt.title(f"Detected centers on {image_filename}")
    # plt.show()

    return components



def compute_homography(image_pts, robot_pts):
    """
    Compute the 3×3 homography matrix mapping image coordinates to robot coordinates.

    Args:
        image_pts (list[tuple[int, int]]): 4 corner points in image coordinates.
        robot_pts (list[tuple[float, float]]): Corresponding 4 corner points in robot coordinates.

    Returns:
        numpy.ndarray: 3×3 homography matrix.
    """
    img_pts = np.array(image_pts, dtype=np.float32)
    rob_pts = np.array(robot_pts, dtype=np.float32)
    H, _ = cv2.findHomography(img_pts, rob_pts)
    return H


def apply_homography(H, point):
    """
    Apply a homography transform to a 2D point.

    Args:
        H: 3×3 homography matrix.
        point: 2D point in image coordinates (x, y).

    Returns:
        list[float, float]: Transformed point [x', y'] in robot coordinates.
    """
    point_vec = np.array([point[0], point[1], 1.0])
    transformed = H @ point_vec
    transformed /= transformed[2]
    return transformed[:2].tolist()


def detect_red_corners(image_path: str, debug: bool = False):
    """
    Detect red calibration dots used to compute the homography.

    Strategy:
        1) HSV thresholding with loose ranges.
        2) Morphological open/close to consolidate blobs.
        3) Optional Lab a‑channel fallback if < 4 points were found.
        4) If > 4 points remain, keep 4 spread‑out points via greedy sampling.

    Args:
        image_path: Path to the image to analyze.
        debug: If True, show a debug window with the ordered points.

    Returns:
        list[tuple[int, int]]: Ordered as [top‑left, top‑right, bottom‑left, bottom‑right].
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Image not found: {image_path}")

    # --- Pass 1: HSV ---
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower1 = np.array([0, 70, 60], dtype=np.uint8)
    upper1 = np.array([10, 255, 255], dtype=np.uint8)
    lower2 = np.array([160, 70, 60], dtype=np.uint8)
    upper2 = np.array([180, 255, 255], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower1, upper1) | cv2.inRange(hsv, lower2, upper2)

    mask = cv2.GaussianBlur(mask, (3, 3), 0)
    k = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=1)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    areas = [cv2.contourArea(c) for c in cnts if cv2.contourArea(c) > 5]
    pts = []
    if areas:
        med = np.median(areas)
        lo, hi = 0.5 * med, 2.0 * med
        for c in cnts:
            a = cv2.contourArea(c)
            if a < lo or a > hi:
                continue
            M = cv2.moments(c)
            if M["m00"] == 0:
                continue
            cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
            pts.append((cx, cy))

    # --- Fallback: Lab a‑channel if < 4 points ---
    if len(pts) < 4:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        a_chan = lab[:, :, 1]
        _, m2 = cv2.threshold(a_chan, 150, 255, cv2.THRESH_BINARY)
        m2 = cv2.morphologyEx(m2, cv2.MORPH_OPEN, k, iterations=1)
        m2 = cv2.morphologyEx(m2, cv2.MORPH_CLOSE, k, iterations=1)
        cnts2, _ = cv2.findContours(m2, cv2.RETR_INTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        pts = []
        areas2 = [cv2.contourArea(c) for c in cnts2 if cv2.contourArea(c) > 5]
        if areas2:
            med2 = np.median(areas2)
            lo2, hi2 = 0.5 * med2, 2.0 * med2
            for c in cnts2:
                a2 = cv2.contourArea(c)
                if a2 < lo2 or a2 > hi2:
                    continue
                M = cv2.moments(c)
                if M["m00"] == 0:
                    continue
                cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
                pts.append((cx, cy))

    if len(pts) < 4:
        raise ValueError(f"Found {len(pts)} red points (<4). Consider tweaking thresholds or crop.")

    # If > 4, keep the 4 most spread‑out points (greedy farthest‑point)
    if len(pts) > 4:
        pts_np = np.array(pts, dtype=np.float32)
        Hh, Ww = img.shape[:2]
        center = np.array([Ww / 2, Hh / 2], dtype=np.float32)
        start = np.argmin(np.linalg.norm(pts_np - center, axis=1))
        chosen = [start]
        while len(chosen) < 4:
            dists = np.min(
                np.linalg.norm(pts_np[:, None, :] - pts_np[chosen][None, :, :], axis=2),
                axis=1,
            )
            dists[chosen] = -1
            chosen.append(int(np.argmax(dists)))
        pts = [tuple(map(int, pts_np[i])) for i in chosen]

    # Order: top‑left, top‑right, bottom‑left, bottom‑right
    pts_sorted = sorted(pts, key=lambda p: (p[1], p[0]))
    top_left, top_right = sorted(pts_sorted[:2], key=lambda p: p[0])
    bot_left, bot_right = sorted(pts_sorted[2:], key=lambda p: p[0])
    ordered = [top_left, top_right, bot_left, bot_right]

    if debug:
        dbg = img.copy()
        for i, (x, y) in enumerate(ordered, 1):
            cv2.circle(dbg, (x, y), 8, (0, 255, 0), -1)
            cv2.putText(dbg, str(i), (x + 6, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.imshow("Red corners", dbg)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return ordered


# ---------- Color logic & placement ----------

def get_radioactive_colors():
    """
    Load color ratios from a JSON file and return the list of color names
    that meet or exceed the "Threshold" ratio.

    Returns:
        list[str]: Subset of {"Green", "Red", "Blue"} considered "radioactive".
    """
    with open(str(PROJECT_ROOT / "color_ratios.json"), "r", encoding="utf-8") as f:
        color_ratios = json.load(f)

    radioactive_colors = []
    if color_ratios["Green"] >= color_ratios["Threshold"]:
        radioactive_colors.append("Green")
    if color_ratios["Red"] >= color_ratios["Threshold"]:
        radioactive_colors.append("Red")
    if color_ratios["Blue"] >= color_ratios["Threshold"]:
        radioactive_colors.append("Blue")
    return radioactive_colors


def get_dominant_color(R: int, G: int, B: int) -> str:
    """
    Determine the dominant color from integer RGB sensor readings.

    Returns:
        "Red", "Green", "Blue", or "Unknown" (if all channels are < 0).
    """
    if max(R, G, B) < 0:
        print(R, G, B)
        return "Unknown"

    if R >= G and R >= B:
        return "Red"
    if G >= R and G >= B:
        return "Green"
    if B >= R and B >= G:
        return "Blue"
    print(R, G, B)
    return "Unknown"


def getcolor() -> None:
    """
    Move to the color sensor, read RGB values, decide whether the cube is radioactive
    based on current thresholds, then queue the appropriate placement motion.
    """
    global ColorSensor_X, ColorSensor_Y, ColorSensor_Z, R, G, B, MAX, \
        Place_radioactive_X, Place_radioactive_Y, Place_radioactive_Z, \
        RedCount, Radioactive_Count, Place_X, Place_Y, Place_Z, \
        Non_Radioactive_Count, GreenCount, BlueCount

    radioactive_color_list = get_radioactive_colors()
    print("Radioactive colors:", radioactive_color_list)

    dType.SetPTPCmdEx(api_conv, 0, ColorSensor_X, ColorSensor_Y, ColorSensor_Z, 0, 1)
    dType.dSleep(1000)
    R = dType.GetColorSensorEx(api_conv, 0)
    G = dType.GetColorSensorEx(api_conv, 1)
    B = dType.GetColorSensorEx(api_conv, 2)
    dType.SetIODOEx(api_conv, 18, 0, 1)  # ensure suction off before placing decision

    MAX = max([R, G, B])
    print("R, G, B:", R, G, B)
    color_cube = get_dominant_color(R, G, B)
    print("Detected cube color:", color_cube)

    if color_cube in radioactive_color_list:
        print(f"Radioactive {color_cube} detected")
        dType.SetPTPCmdEx(api_conv, 0, Place_radioactive_X, Place_radioactive_Y, Place_radioactive_Z, 0, 1)
        Radioactive_Count = Radioactive_Count + 1
        Sort_Radioactive()
    else:
        print(f"Non‑radioactive {color_cube} detected")
        dType.SetPTPCmdEx(api_conv, 0, Place_X, Place_Y, Place_Z, 0, 1)
        Non_Radioactive_Count = Non_Radioactive_Count + 1
        Sort_Non_Radioactive()

    dType.dSleep(1000)
    dType.SetEMotorEx(api_conv, 1, 1, -int(6000), 1)


def Is_Suction_On() -> None:
    """Log current suction control and object detection state from the end effector."""
    ctrl_enabled, is_sucked = dType.GetEndEffectorSuctionCup(api_conv)
    print(f"Suction enabled: {ctrl_enabled}, Object detected: {is_sucked}")


def Sort_Non_Radioactive() -> None:
    """Release the cube and resume the conveyor for the non‑radioactive bin."""
    dType.SetEndEffectorSuctionCupEx(api_conv, 0, 1)
    dType.SetPTPCmdEx(api_conv, 0, -33,  -216,  80, 0, 1)
    dType.SetEMotorEx(api_conv, 0, 1, int(8000), 1)
    dType.dSleep(4000)
    dType.SetEMotorEx(api_conv, 0, 0, int(0), 1)



def Sort_Radioactive() -> None:
    """Release the cube and run the belt in reverse for the radioactive bin."""
    dType.SetEndEffectorSuctionCupEx(api_conv, 0, 1)
    dType.SetPTPCmdEx(api_conv, 0, -33,  -216,  80, 0, 1)
    dType.SetEMotorEx(api_conv, 0, 1, -int(8000), 1)
    dType.dSleep(5000)
    dType.SetEMotorEx(api_conv, 0, 0, int(0), 1)



def detect_next_component():
    """
    Capture an image, detect components in the camera frame, and return the first one
    converted to robot coordinates (x_loc, y_loc).

    Returns:
        tuple[float | None, float | None]: (x_loc, y_loc) in robot coordinates,
        or (None, None) if no component was detected.
    """
    global homography_done, H_0, cap

    path_image = take_snapshot(
        "Logi C270 HD WebCam",
        str(PROJECT_ROOT / "Keypoint_detection" / "dataset" / "test" / "images" / "capture_2.jpg")
    )

    red_corner = detect_red_corners(path_image, debug=False)

    if not homography_done:
        print("Computing homography…")
        H_0 = compute_homography(red_corner, points_robot)
        homography_done = True
        print("✅ Homography computed successfully.")

    components_cam = Find_cubes(path_image)  # Detect components in image frame

    try:
        requests.post("http://localhost:5000/notify_image_update")
        print("notify_image_update ok")
    except Exception as e:
        print(e)

    # Take the first detected component
    try:
        comp = components_cam[0]
    except Exception:
        return None, None

    x_cam, y_cam = comp["x"], comp["y"]
    x_loc, y_loc = apply_homography(H_0, (x_cam, y_cam))

    pose = dType.GetPose(api_conv)
    # print("Distance :",np.sqrt((pose[0]- x_loc)**2 + (pose[1]- y_loc)**2))
    print("distance hyopot :", np.hypot(pose[0] - x_loc, pose[1] - y_loc))
    

    MAX_DIST_MM = 200
    if np.hypot(pose[0] - x_loc, pose[1] - y_loc) > MAX_DIST_MM:
        print("Wrong cube detected — trying other candidates")

        for comp in components_cam:
            # comp: {"x": x_px, "y": y_px, "z": -60}
            x_loc_i, y_loc_i = apply_homography(H_0, (comp["x"], comp["y"]))  # -> robot
            d = np.hypot(x_loc_i - pose[0], y_loc_i - pose[1])
            # debug facultatif
            # print(f"Candidate @ ({x_loc_i:.1f}, {y_loc_i:.1f}) -> d={d:.1f} mm")

            if d <= MAX_DIST_MM:
                return x_loc_i, y_loc_i
        
        print("No valid cube within threshold — skipping this cycle")
        return None, None

    return x_loc, y_loc


# ===============================
#       Configuration & State
# ===============================
BASE_DIR = str(PROJECT_ROOT)

# Camera parameters
# camera_index = 0  # Change to 2 or 3 if this is not the correct camera
save_directory = os.path.join(BASE_DIR, "Bounding_box_detection", "dataset", "test", "images")
filename = "capture_dobot_conv_1.jpg"
save_path = os.path.join(save_directory, filename)

# Robot‑frame coordinates of the 4 calibration dots (order matched in detect_red_corners)
points_robot = [
    [-54.6578, -96.0],       # top‑left
    [-77.1862, -205.4147],   # top‑right
    [-104.0, -104.5372],     # bottom‑left
    [-113.4321, -205.8813],  # bottom‑right
]

# Conveyor & placement positions (mm)
ColorSensor_X = -48.86
ColorSensor_Y = -236.52
ColorSensor_Z = 45
Place_X = 151
Place_Y = -163
Place_Z = 15
Place_radioactive_X = 150
Place_radioactive_Y = 134
Place_radioactive_Z = 15

# Stepper constants for the belt (kept for parity with original)
STEP_PER_CRICLE = 360.0 / 1.8 * 10.0 * 16.0
MM_PER_CRICLE = 3.1415926535898 * 36.0
vel = float(30) * STEP_PER_CRICLE / MM_PER_CRICLE

# Runtime counters / flags
RedCount = 0
BlueCount = 0
GreenCount = 0
Radioactive_Count = 0
Non_Radioactive_Count = 0

# Global runtime state
api_conv = None
cap = None
homography_done = False
H_0 = None
R = G = B = MAX = 0

# NOTE: The original script had a late line `BASE_DIR = ""`, which would clear the base path
# and break model/result paths. It has been intentionally omitted to preserve correct behavior.


# ===============================
#              Runtime
# ===============================
# Connect to Dobot (conveyor)
try:
    api_conv = dType.load()
    port_conv = get_port("convoyeur")
    state_conv = dType.ConnectDobot(api_conv, port_conv, 115200)
except Exception as e:
    print("Connection problem:", e)

# Prepare command queue & sensors
dType.SetQueuedCmdClear(api_conv)
dType.SetQueuedCmdStartExec(api_conv)
dType.SetColorSensor(api_conv, 1, 1, 1)
dType.SetInfraredSensor(api_conv, 1, 2, 1)
dType.dSleep(1000)
dType.SetPTPCmdEx(api_conv, 0, -33, -216, 80, 0, 1)

# Initialize camera

# Register signals only after api and camera are set
if os.name == "nt":
    signal.signal(signal.SIGBREAK, handle_sigterm)  # CTRL_BREAK_EVENT → SIGBREAK
    signal.signal(signal.SIGINT, handle_sigterm)    # safety
else:
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

# Start the belt motor (as in original)
dType.SetEMotorEx(api_conv, 1, 1, -int(8000), 1)

# Main loop
while True:
    if dType.GetInfraredSensor(api_conv, 2)[0] == 1:
        dType.SetEMotorEx(api_conv, 1, 0, int(0), 1)  # stop conveyor

        x_loc, y_loc = detect_next_component()
        print("COMP:", x_loc, y_loc)

        if x_loc is None and y_loc is None:
            print("🛑 No cube detected. Ending cycle.")
            break

        dType.SetEndEffectorSuctionCupEx(api_conv, 1, 1)
        dType.SetPTPCmdEx(api_conv, 2, x_loc, y_loc, 50, 0, isQueued=1)
        dType.SetPTPCmdEx(api_conv, 2, x_loc, y_loc, 10, 0, isQueued=1)

        getcolor()

# Cleanup
try:
    dType.SetQueuedCmdStopExec(api_conv)
finally:
    dType.DisconnectDobot(api_conv)

# Explicitly free DLL handle (Windows)
from ctypes import windll
windll.kernel32.FreeLibrary.argtypes = [ctypes.c_void_p]
windll.kernel32.FreeLibrary(api_conv._handle)
