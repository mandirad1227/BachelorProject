# paths.py
from pathlib import Path
import sys, os

def find_project_root(markers=("requirements.txt", "pyproject.toml", ".git", ".project-root")) -> Path:
    """Walk up from this file until a project marker is found."""
    p = Path(__file__).resolve().parent
    while True:
        if any((p / m).exists() for m in markers):
            return p
        if p.parent == p:  # reached filesystem root
            return Path(__file__).resolve().parent  # fallback: folder of this file
        p = p.parent

# --- Base paths ---
PROJECT_ROOT = find_project_root()
PYTHON_EXE   = Path(sys.executable)  # always the currently active Python (your venv if activated)

# --- Dobot SDK directory (relative to project root) ---
# Default: "<project>/Python_project" ; optional env override ; optional legacy fallback "Python project"
_env = os.environ.get("DOBOT_SDK_DIR")
DOBOT_SDK_DIR = Path(_env) if _env else (PROJECT_ROOT / "Python_project")
if not DOBOT_SDK_DIR.exists():
    legacy = PROJECT_ROOT / "Python_project"  # legacy name with a space, just in case
    if legacy.exists():
        DOBOT_SDK_DIR = legacy

def ensure_dobot_importable() -> None:
    """
    Add the Dobot SDK folder to Python import paths and (on Windows) to the DLL search path.
    Uses only project-relative paths (no raw strings, no absolute host-specific paths).
    """
    sdk = DOBOT_SDK_DIR

    if not sdk.exists():
        raise FileNotFoundError(
            f"Dobot SDK not found at: {sdk}\n"
            f"→ Ensure the folder exists and contains 'DobotDll.dll', or set DOBOT_SDK_DIR env var."
        )

    # Allow importing DobotDllType.py
    if str(sdk) not in sys.path:
        sys.path.insert(0, str(sdk))

    # Allow Windows loader to find DobotDll.dll
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(sdk))
