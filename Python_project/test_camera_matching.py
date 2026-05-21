import cv2
try:
    from pygrabber.dshow_graph import FilterGraph
except Exception:
    FilterGraph = None

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
    Open a camera by friendly name by first resolving to a DSHOW index, then opening by index.
    Tries CAP_DSHOW first, then CAP_MSMF as fallback.
    """
    idx = resolve_index_by_name(name)
    if idx is None:
        devices = list_cameras_dshow()
        raise RuntimeError(f"Camera '{name}' not found. Available: {devices}")

    for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF):
        cap = cv2.VideoCapture(idx, backend)
        if cap.isOpened():
            return cap

    raise RuntimeError(f"Could not open camera '{name}' at index {idx} using DSHOW/MSMF.")

def open_two_cameras(name_a: str, name_b: str) -> tuple[cv2.VideoCapture, cv2.VideoCapture]:
    """
    Open two distinct cameras by name without collisions. Raises if same device or already in use.
    """
    idx_a = resolve_index_by_name(name_a)
    idx_b = resolve_index_by_name(name_b)
    if idx_a is None or idx_b is None:
        raise RuntimeError(f"Not found: {name_a if idx_a is None else ''} {name_b if idx_b is None else ''}")

    if idx_a == idx_b:
        raise RuntimeError(f"Both names resolve to the same device index {idx_a}. Check device names.")

    cap_a = open_camera_by_name(name_a)
    cap_b = open_camera_by_name(name_b)
    return cap_a, cap_b


cams = list_cameras_dshow()
print("DirectShow devices (index -> name):")
for i, n in enumerate(cams):
    print(f"[{i}] {n}")