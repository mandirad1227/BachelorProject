"""
Asynchronous scenario for the rail‑mounted Dobot (vision‑guided pick & place)
-----------------------------------------------------------------------------
Purpose
    Control a Dobot Magician mounted on a linear rail to pick a detected cube (YOLOv8)
    and drop it at a target location. The robot keeps a fixed distance r from the cube
    by splitting the motion between the rail translation and the local robot pose.

High‑level pipeline
    1) Initialize camera and the rail Dobot (DLL connection, enable rail, suction IO).
    2) Capture an image, detect the 4 red calibration dots, compute homography H₀ (image → robot).
    3) Detect cubes with YOLOv8 and take the first one.
    4) Convert its image center to robot coordinates and compute (rail_x, x_local, y_local)
       to keep a constant distance r from the cube.
    5) Execute pick‑and‑place: approach, suction on, lift, translate along rail, drop, return.
    6) Loop while there are components to process.

Notes / prerequisites
    - Windows with the Dobot SDK available (DobotDllType.py + DobotDll.dll) and importable.
    - Paths are machine‑specific and should be adapted as needed.
    - CTRL_BREAK (Windows) / SIGTERM/SIGINT triggers an emergency stop that disconnects cleanly.
"""

# ===============================
#              Imports
# ===============================
import os
import sys
import time
import math
import signal
import shutil
from statistics import mean

import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
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
# Suction state (kept for compatibility with other modules if referenced)

def handle_sigterm(signum, frame):
    """
    Signal handler (emergency stop): stop motors, release the camera, turn suction off,
    disconnect from Dobot DLL, then exit the process.
    """
    print("🛑 SIGBREAK/SIGTERM received, emergency stop for Dobot Rail")
    if api_rail:
        try:
            dType.SetEMotorEx(api_rail, 1, 0, int(0), 1)
            dType.SetEMotorEx(api_rail, 0, 0, int(0), 1)
            try :
                cap.release()
            except Exception as e :
                print(e)
            dobot_emergency_stop(api_rail)
            dType.DisconnectDobot(api_rail)
        except Exception as e:
            print(f"⚠️ Error during emergency stop: {e}")
            dType.DisconnectDobot(api_rail)
    sys.exit(0)


# Signal mapping (Windows vs others)
if os.name == "nt":
    # CTRL_BREAK_EVENT triggers SIGBREAK
    signal.signal(signal.SIGBREAK, handle_sigterm)
    # Also capture SIGINT (CTRL_C_EVENT) for safety
    signal.signal(signal.SIGINT, handle_sigterm)
else:
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)


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


def compute_local_pick_point(image_point, r=255):
    """
    Compute the rail position and the local robot coordinates needed to pick a cube
    while keeping a fixed distance ``r`` from the cube center.

    Concept
        - Convert the cube center in image coordinates (x_img, y_img) to robot coordinates
          (X_cube, Y_cube) using the global homography ``H_0``.
        - Decompose the fixed distance ``r`` into a local Y offset (triangle relation) and a rail
          translation so that the robot stays at distance ``r`` from the cube.

    Args:
        image_point (tuple[int, int]): The cube center (x, y) in pixels (camera frame).
        r (float): Desired robot‑to‑cube distance in mm. Default: 255.

    Returns:
        tuple[float, float, float]: (rail_x, x_local, y_local)
            - rail_x: rail target position (mm)
            - x_local: local X coordinate (mm) relative to robot base frame
            - y_local: local Y coordinate (mm) relative to robot base frame
    """
    global H_0

    X_cube, Y_cube = apply_homography(H_0, image_point)

    try:
        Y_local = np.sqrt(r**2 - X_cube**2)
    except Exception as e:
        Y_local = 0
        print("Exception:", e)

    rail_x = np.abs(Y_cube - Y_local)

    # Convention: x_local > 0 in front of the robot
    x_local = X_cube

    return rail_x, x_local, Y_local


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
        conf=0.5,
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
    Compute the 3×3 homography mapping image coordinates to robot coordinates.

    Args:
        image_pts (list[tuple[int, int]]): 4 points (x, y) in image coordinates.
        robot_pts (list[tuple[float, float]]): 4 corresponding points (X, Y) in robot frame.

    Returns:
        numpy.ndarray: The 3×3 homography matrix.
    """
    img_pts = np.array(image_pts, dtype=np.float32)
    rob_pts = np.array(robot_pts, dtype=np.float32)
    H, _ = cv2.findHomography(img_pts, rob_pts)
    return H


def apply_homography(H, point):
    """
    Apply a homography to a 2D point (x, y).

    Args:
        H (numpy.ndarray): 3×3 homography matrix (image → robot).
        point (tuple[int, int]): Point in image coordinates.

    Returns:
        list[float, float]: Transformed point in robot coordinates [X', Y'].
    """
    point_vec = np.array([point[0], point[1], 1.0])
    transformed = H @ point_vec
    transformed /= transformed[2]
    print("In robot frame, the coordinate is:", transformed[:2].tolist())
    return transformed[:2].tolist()

def _group_close(values, sensitivity):
    """
    Group numeric values that are within tolerance of each other.
    Returns list of groups (each group is list of original values).
    """
    groups = []
    for v in values:
        placed = False
        for g in groups:
            if abs(v - mean(g)) <= sensitivity:
                g.append(v)
                placed = True
                break
        if not placed:
            groups.append([v])
    return groups

def calculate_last_corner(corners, sensitivity=20.0):
    """
    corners: iterable of three (x,y) pairs (floats or ints)
    sensitivity: tolerance for considering coordinates equal (same units as coordinates)
    Returns: (x,y) tuple for the missing fourth corner (floats)
    """
    # Makes sure that there are only 3 corners as the functions expects that
    if len(corners) != 3:
        raise ValueError("Expected exactly 3 corner points")

    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]

    x_groups = _group_close(xs, sensitivity)
    y_groups = _group_close(ys, sensitivity)

    # Function to help find 
    def choose_missing(groups):
        # If we have 2 groups we choose the group that has a unique value, as that is the missing corner
        if len(groups) == 2:
            if len(groups[0]) == 1 and len(groups[1]) == 2:
                return mean(groups[0]), mean(groups[1])
            if len(groups[1]) == 1 and len(groups[0]) == 2:
                return mean(groups[1]), mean(groups[0])
        # If we only have one group then that means all the corner points are rougly the same area or the sensitiviy is off
        if len(groups) == 1:
            raise ValueError("Could not find two similar values, either adjust sensitivity or there is false corners.")
        # if we have 3 groups then it finds each corner unique, and we have to adjust sensitiviy or something is wrong with the camera reading.
        if len(groups) == 3:
            raise ValueError("Could not find two similar values, either adjust sensitivity or there is false corners.")
        # Worst case it returns the mean of the first groups
        vals = [mean(g) for g in groups]
        if len(vals) >= 2:
            return vals[0], vals[1]
        return mean(groups[0]), mean(groups[0])

    x_single, x_paired = choose_missing(x_groups)
    y_single, y_paired = choose_missing(y_groups)
    if (float(x_single),float(y_single)) in corners:
        raise ValueError("Got one of the points that was inputed out, should not happen. Likely a rogue point not part of the zone.")
    return (float(x_single), float(y_single))


def detect_red_corners(image_path, debug=True):
    """
    Detect four red dots (corners) for homography calibration.

    Args:
        image_path (str): Path to the image.
        debug (bool): If True, show a debug window with detected points.

    Returns:
        list[tuple[int, int]]: 4 coordinates ordered as [top‑left, top‑right, bottom‑left, bottom‑right].

    Raises:
        FileNotFoundError: If the image cannot be read.
        ValueError: If the number of detected red points is not equal to 4.
    """
    print("Detecting red corners…")
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image not found: {image_path}")

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Red mask (two ranges due to HSV wraparound)
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)

    # Denoising
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    red_corners = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        print("area:", area)
        if 60 < area < 300:
            M = cv2.moments(cnt)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                red_corners.append((cx, cy))

    print("we have:", len(red_corners), "corners")
    if len(red_corners) == 3:
        print("3 corners detected; calculating last corner")
        for corner in range(len(red_corners)):
            print(f"Corner {corner}: {red_corners[corner]}")
        last_corner = calculate_last_corner(red_corners)
        red_corners.append(last_corner)
        print(f"Last corner: {last_corner}")
        
    if len(red_corners) != 4:
        debug_image = image.copy()
        for i, (x, y) in enumerate(red_corners):
            cv2.circle(debug_image, (x, y), 10, (255, 0, 255), -1)
            cv2.putText(
                debug_image,
                str(i + 1),
                (x + 10, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )
        cv2.imshow("Detected Corners", debug_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        raise ValueError(f"❌ Found {len(red_corners)} red points, 4 required.")

    # Custom ordering based on the image orientation
    red_corners_sorted = sorted(red_corners, key=lambda p: p[1])
    top_two = sorted(red_corners_sorted[:2], key=lambda p: p[0])  # top‑left, top‑right
    bottom_two = sorted(red_corners_sorted[2:], key=lambda p: p[0])  # bottom‑left, bottom‑right

    # Final order: bottom‑left, top‑left, top‑right, bottom‑right
    ordered = [bottom_two[0], top_two[0], top_two[1], bottom_two[1]]

    if debug:
        debug_image = image.copy()
        for i, (x, y) in enumerate(ordered):
            cv2.circle(debug_image, (x, y), 10, (255, 0, 255), -1)
            cv2.putText(
                debug_image,
                str(i + 1),
                (x + 10, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )
        cv2.imshow("Detected Corners", debug_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return ordered


def detect_next_component():
    """
    Capture an image, detect components in the camera frame, and return the first one
    converted to robot + rail coordinates.

    Returns:
        tuple[float, float, float]: (rail_x, x_local, y_local) where
            - rail_x: rail target position (mm)
            - x_local, y_local: local coordinates for approach and pick
        or (None, 0, 0) if nothing is detected.
    """
    global homography_done, H_0, cap

    path_image = take_snapshot(
        "C505e HD Webcam",
        str(PROJECT_ROOT / "Keypoint_detection" / "dataset" / "test" / "images" / "capture_1.jpg")
    )
    
    red_corner = detect_red_corners(path_image, debug=False)

    if not homography_done:
        print("Computing homography…")
        H_0 = compute_homography(red_corner, points_robot)
        homography_done = True
        print("✅ Homography computed successfully.")

    components_cam = Find_cubes(path_image)  # detection in image frame

    # Note: logic kept intact (first item is accessed before emptiness check in original code)
    comp = components_cam[0]
    x_cam, y_cam = comp["x"], comp["y"]
    rail_x, x_loc, y_loc = compute_local_pick_point((x_cam, y_cam))

    if not components_cam:
        print("🔍 No components detected.")
        return None, 0, 0

    try:
        requests.post("http://localhost:5000/notify_image_update")
    except Exception as e:
        print(e)

    return rail_x, x_loc, y_loc


def pick_and_place(rail_x, x_loc, y_loc):
    """
    Execute the pick‑and‑place sequence:
        1) Rail translation
        2) Z approach
        3) Suction ON
        4) Lift
        5) Rail translation to the drop zone
        6) Drop (suction OFF)
        7) Return to waiting pose

    Args:
        rail_x (float): Rail target position (mm)
        x_loc (float): Local X coordinate (mm)
        y_loc (float): Local Y coordinate (mm)
    """
    z = -113  # approach depth (adapt)
    rail_pos = 575

    current_pose = dType.GetPose(api_rail)
    dType.SetPTPWithLCmdEx(api_rail, 1, x_loc, y_loc, LIFT_Z, 0, rail_x, 1)  # move rail to x

    current_pose = dType.GetPose(api_rail)
    dType.SetPTPCmdEx(api_rail, 2, x_loc, y_loc, z, current_pose[3], 1)  # pick the cube
    dType.SetEndEffectorSuctionCupEx(api_rail, 1, 1)

    current_pose = dType.GetPose(api_rail)
    dType.SetPTPCmdEx(api_rail, 2, x_loc, y_loc, LIFT_Z, current_pose[3], 1)  # lift the cube

    current_pose = dType.GetPose(api_rail)
    dType.SetPTPWithLCmdEx(api_rail, 2, 222, 0, LIFT_Z, current_pose[3], rail_pos, 1)  # move to rail pos

    current_pose = dType.GetPose(api_rail)
    dType.SetPTPCmdEx(api_rail, 2, 222, 0, LIFT_Z, current_pose[3], 1)

    current_pose = dType.GetPose(api_rail)
    dType.SetPTPCmdEx(api_rail, 2, DROP_X, DROP_Y, LIFT_Z, current_pose[3], 1)

    current_pose = dType.GetPose(api_rail)
    dType.SetPTPCmdEx(api_rail, 2, DROP_X, DROP_Y, DROP_Z, current_pose[3], 1)
    dType.SetEndEffectorSuctionCupEx(api_rail, 0, 1)

    current_pose = dType.GetPose(api_rail)
    dType.SetPTPCmdEx(api_rail, 2, DROP_X, DROP_Y, LIFT_Z, current_pose[3], 1)

    current_pose = dType.GetPose(api_rail)
    dType.SetPTPWithLCmdEx(api_rail, 1, 222, 0, LIFT_Z, current_pose[3], 45, 1)  # waiting pose


# ===============================
#       Configuration & State
# ===============================
BASE_DIR = str(PROJECT_ROOT)

# Camera parameters
camera_name = " Logi C270 HD WebCam"  # Set to 2 or 0 depending on your camera
save_directory = os.path.join(BASE_DIR, "Bounding_box_detection", "dataset", "test", "images")
filename = "capture_1.jpg"
save_path = os.path.join(save_directory, filename)

# Demo image & derived paths
Nom_Img = "capture1.jpg"
image_path = os.path.join(BASE_DIR, "Bounding_box_detection", "dataset", "test", "images", Nom_Img)
save_path = os.path.join(
    BASE_DIR, "Bounding_box_detection", "dataset", "test", "images", "cropped", Nom_Img
)

# JSON inputs/outputs (kept for parity with original script)
json_input = os.path.join(BASE_DIR, "positions.json")
json_output = os.path.join(BASE_DIR, "positions_robot.json")

# Robot‑frame coordinates of the 4 calibration dots (adjust to your setup)
points_robot = [
    [278.0, 127.0],  # top‑left
    [277.5, 32.9],   # top‑right
    [85.0, 30.1],    # bottom‑left
    [86.2, 125.5],   # bottom‑right
]

# Drop pose and heights (adapt to your scene)
DROP_X = 99.4
DROP_Y = -186
DROP_Z = -60
DROP_Rail = 575
LIFT_Z = 0

# Runtime state
api_rail = None
cap = None
homography_done = False
H_0 = 0
rail_x = 0
suction_state = True


# ===============================
#            Runtime
# ===============================


# Dobot setup & connection
try:
    print("🔧 Loading DLL…")
    api_rail = dType.load()
    print("✅ DLL loaded")

    print("🔌 Getting port…")
    port_rail = get_port("rail")
    print("✅ Port:", port_rail)

    print("🔗 Connecting to Dobot…")
    state_rail = dType.ConnectDobot(api_rail, port_rail, 115200)
    print("✅ Connected, state:", state_rail)

    # Short delay for the external controller to come up
    time.sleep(0.8)

    # (Optional) stop/clear queue before config
    try:
        dType.SetQueuedCmdStopExec(api_rail)
        dType.SetQueuedCmdClear(api_rail)
    except Exception:
        pass

    print("⚙️ Enabling rail (SetDeviceWithL)…")
    enabled = False
    for attempt in range(3):
        try:
            # Most wrappers: SetDeviceWithL(api, enable, isQueued=0) -> [queuedIdx]
            qidx = dType.SetDeviceWithL(api_rail, 1, 0)
            time.sleep(0.2)
            enabled = True
            print(f"✅ Rail enable command sent (queued {qidx})")
            break
        except Exception as e:
            print(f"⚠️ Enable rail attempt {attempt + 1} failed: {e}")
            time.sleep(0.3)

    if not enabled:
        print("❌ Rail enable failed after retries. Check power/cable/controller.")
        # raise RuntimeError("Rail not enabled")

    # Start queue execution if you plan to send queued PTP/LINEAR moves
    try:
        dType.SetQueuedCmdStartExec(api_rail)
    except Exception:
        pass

    print("🔌 Enabling suction cup (IO)…")
    dType.SetIODOEx(api_rail, 18, 1)
    print("✅ IO activated")

    print("🎉 Rail initialized")
except Exception as e:
    print("❌ Exception caught:", e)

print("✔️ End of rail init block")

# Main loop
while True:
    try:
        rail_x, x_loc, y_loc = detect_next_component()

        if rail_x is None:
            print("🛑 No cube detected. Ending cycle.")
            break

        print("Component:", x_loc, y_loc, "— Required rail:", rail_x)
        pick_and_place(rail_x, x_loc, y_loc)
        time.sleep(0.5)  # small pause for stabilization

    except Exception as e:
        print(f"⚠️ Error during cycle: {e}")
        break

# Clean disconnection
dType.DisconnectDobot(api_rail)
