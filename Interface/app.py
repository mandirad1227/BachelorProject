"""
Flask + Socket.IO web app for controlling two Dobot robots (rail + conveyor)
--------------------------------------------------------------------------
Purpose
    Provide a simple web dashboard to:
      - Start/stop scenarios (rail + conveyor) and homing sequences via helper scripts.
      - Persist color ratio thresholds used by the conveyor color sorting scenario.
      - Stream live logs to the UI and notify when a new annotated image is available.

High‑level flow
    1) Initialize Flask + Socket.IO (eventlet based) and set up routes.
    2) Allow the user to toggle tables, trigger emergency stop, run homing, and launch scenarios.
    3) Persist color thresholds to `color_ratios.json`.
    4) Expose `/notify_image_update` to let worker scripts refresh images on the page.

Notes / prerequisites
    - Windows with the Dobot SDK available and importable (DobotDllType.py + DobotDll.dll).
    - This app spawns worker scripts or functions provided in `launcher.py` (no logic change here).
    - Eventlet is used; monkey_patch must happen before importing/using networking libs.
"""

# ===============================
#         Eventlet first
# ===============================
import eventlet
eventlet.monkey_patch()


# ===============================
#              Imports
# ===============================
import os
import sys
import json
import time
import threading
import subprocess
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]   # parent of Interface/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from paths import PROJECT_ROOT, PYTHON_EXE as VENV_PYTHON, ensure_dobot_importable

# Make the Dobot SDK (Python stubs + DobotDll.dll) importable
ensure_dobot_importable()

# Ensure project-level modules (e.g., get_port, launcher, scenarios/…) are importable
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Now these imports will succeed without hardcoded paths
import DobotDllType as dType
from get_port import get_port
from launcher import launch_scenario, launch_homing, emergency_stop


# ===============================
#   Configuration & global state
# ===============================
# Paths to external Python and helper scripts (adapt to your environment)

# Use the current virtualenv's Python for any subprocess calls
PYTHON_EXE = str(VENV_PYTHON)

# SDK helper scripts shipped with the Dobot package
# (folder renamed at the project root to "Python project")
SIMU_SCRIPT = str(PROJECT_ROOT / "Python project" / "test_Dobot1.py")
HOME_SCRIPT = str(PROJECT_ROOT / "Python project" / "Home.py")
STOP_SCRIPT = str(PROJECT_ROOT / "Python project" / "Stop.py")

# Project files and folders
LOG_PATH     = str(PROJECT_ROOT / "log_detection.txt")
IMAGE_FOLDER = PROJECT_ROOT / "Interface" / "static" / "images"  # Path object is fine; cast to str if an API needs it
INIT_FILE    = str(PROJECT_ROOT / "system_initialized.flag")
COLOR_FILE   = str(PROJECT_ROOT / "color_ratios.json")

# Shared state used by the UI (populated elsewhere in the project)
all_dobots = []  # items may expose .name, .status, .connected, .emergency_stop()

dobots_config = [
    ("rail", "Dobot1"),
    ("convoyeur", "Dobot2"),
]

# Socket.IO background thread guard
thread_started = False


# ===============================
#          App factories
# ===============================
app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")


# ===============================
#          Helper functions
# ===============================

def get_dobot_status() -> list[dict]:
    """
    Serialize the current status of all known Dobots for the UI.

    Returns:
        A list of dictionaries like {"name": str, "status": Any}.
    """
    return [{"name": r.name, "status": r.status} for r in all_dobots]


def run_and_log(script_path: str) -> None:
    """
    Run a Python script in a subprocess and stream stdout to ``LOG_PATH``.

    Args:
        script_path: Absolute path to the Python script to execute.
    """
    process = subprocess.Popen(
        [PYTHON_EXE, script_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
    )
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        for line in process.stdout:  # type: ignore[attr-defined]
            f.write(line)
            f.flush()


# ----- Color ratio persistence -----

def _fr_to_en_keys(d: dict) -> dict:
    """Return a copy with French color keys mapped to English keys."""
    mapping = {"Vert": "Green", "Rouge": "Red", "Bleu": "Blue", "Seuil": "Threshold"}
    return {mapping.get(k, k): v for k, v in d.items()}


def _en_to_fr_keys(d: dict) -> dict:
    """Return a copy with English color keys mapped to French keys (for UI display)."""
    mapping = {"Green": "Vert", "Red": "Rouge", "Blue": "Bleu", "Threshold": "Seuil"}
    return {mapping.get(k, k): v for k, v in d.items()}


def read_color_ratios() -> dict:
    """
    Read color ratios from ``COLOR_FILE``.

    Returns:
        A dict with **French** keys (Vert, Rouge, Bleu, Seuil) for compatibility with templates.
        File contents may be stored with English keys; we map them back for the UI.
    """
    if not os.path.exists(COLOR_FILE):
        return {"Vert": 0.0, "Rouge": 0.0, "Bleu": 0.0, "Seuil": 0.0}

    with open(COLOR_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # If the file uses English keys (preferred for worker scripts), map to French for display
    if {"Green", "Red", "Blue", "Threshold"}.issubset(set(data.keys())):
        return _en_to_fr_keys(data)

    # Already in French
    return data


def save_color_ratios(ratios: dict) -> None:
    """
    Persist color ratios to ``COLOR_FILE``.

    We always **write English keys** (Green, Red, Blue, Threshold) so worker scripts
    like the conveyor scenario can read them directly. UI continues to use French labels.

    Args:
        ratios: Dict with French keys from the form (Vert, Rouge, Bleu, Seuil).
    """
    data_en = _fr_to_en_keys(ratios)
    with open(COLOR_FILE, "w", encoding="utf-8") as f:
        json.dump(data_en, f, indent=4)


# ===============================
#               Routes
# ===============================
@app.route("/notify_image_update", methods=["POST"])
def notify_image_update():
    """Web‑hook called by worker scripts to request an image refresh on the UI."""
    socketio.emit("update_image")
    return "", 204


@app.route("/", methods=["GET", "POST"])
def index():
    """
    Main user page: toggle tables, emergency stop, homing, launch scenarios,
    and update color ratios.
    """
    print("✅ [DEBUG] Request:", request.method, request.form)

    if "show_tables" not in session:
        session["show_tables"] = True  # default: show tables

    status = ""
    color_ratios = read_color_ratios()  # dict with FR keys for UI

    if request.method == "POST":
        if "toggle_tables" in request.form:
            session["show_tables"] = not session["show_tables"]

        elif "stop" in request.form:
            emergency_stop()  # ⛔ stop running scenarios (rail + conveyor)
            for r in all_dobots:
                if getattr(r, "connected", False):
                    try:
                        r.emergency_stop()  # ⛔ halt motion if currently driven from Flask
                    except Exception:
                        pass
            status = "🛑 Emergency stop executed."

        elif "home" in request.form and request.form.get("home") == "1":
            print("DEBUG: HOMING trigger")
            launch_homing()  # from launcher
            status = "Homing "

        elif "save_ratios" in request.form:
            try:
                # Accept FR form fields and persist as EN keys
                ratios_fr = {
                    "Vert": float(request.form["Vert"]),
                    "Rouge": float(request.form["Rouge"]),
                    "Bleu": float(request.form["Bleu"]),
                    "Seuil": float(request.form["Seuil"]),
                }
                save_color_ratios(ratios_fr)
                color_ratios = ratios_fr  # reflect back to UI
                status = "Color ratios updated."
            except Exception:
                status = "❌ Error updating color ratios."

        elif "lancer_scenario" in request.form:
            if all(getattr(r, "connected", False) for r in all_dobots):
                if not os.path.exists(INIT_FILE):
                    return redirect(url_for("initialize"))
                mode = request.form.get("scenario_mode")
                status = f"Launching scenario: {mode}"
                threading.Thread(target=launch_scenario, args=(mode,), daemon=True).start()
            else:
                status = "⚠️ Both Dobots must be connected before launching the scenario."

    show_tables = session.get("show_tables", True)
    etats_dobots = get_dobot_status()
    return render_template(
        "index.html",
        status=status,
        color_ratios=color_ratios,
        etats_dobots=etats_dobots,
        show_tables=show_tables,
    )



@app.route("/logs")
def logs():
    """Return live logs captured from worker processes (plain text)."""
    if not os.path.exists(LOG_PATH):
        return "No logs available."
    with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ===============================
#        Socket.IO events
# ===============================
@socketio.on("connect")
def test_connect():
    """Push an initial status and ensure the background thread is started once."""
    global thread_started
    print("✅ Client connected to WebSocket")

    # socketio.emit("update_dobot_status", [{"name": "Dobot1", "status": "Test"}])

    if not thread_started:
        print("🔁 Starting background task via start_background_task")
        thread_started = True
        # socketio.start_background_task(background_dobot_status)


# ===============================
#            Runtime
# ===============================
if __name__ == "__main__":
    # threading.Thread(target=background_dobot_status, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False)

# http://10.212.66.45:5000/
# http://10.213.55.151/5000/
