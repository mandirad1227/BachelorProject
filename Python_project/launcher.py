"""
Subprocess launcher utilities for scenarios & homing
---------------------------------------------------
Purpose
    Start/stop the asynchronous scenario pair (rail + conveyor), trigger homing
    for both robots, and perform a soft emergency stop on running child processes.

Functions
    - launch_scenario(mode): Launch "async" scenario processes for rail & conveyor.
    - launch_homing(): Run homing scripts for both robots and wait for completion.
    - dobot_emergency_stop(api): DLL-level emergency stop helper for a given API handle.
    - emergency_stop(): Send CTRL_BREAK to running child processes and wait/kill.

Notes
    - Paths are machine-specific; adjust constants below to your environment.
    - The import from `scenarios.scenario_sync` is kept for parity, even if unused here.
"""

# ===============================
#              Imports
# ===============================
import signal
import subprocess
from pathlib import Path
import sys
_root = Path(__file__).resolve().parent
for _ in range(6):  # goes up to 6 levels if needed
    if (_root / "paths.py").exists():
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        break
    _root = _root.parent
# --------------------------------------------------------------------------

from paths import PROJECT_ROOT, PYTHON_EXE as VENV_PYTHON, ensure_dobot_importable
ensure_dobot_importable()
# Make the project root & Dobot SDK available without hardcoded paths
from paths import PROJECT_ROOT, PYTHON_EXE as VENV_PYTHON, ensure_dobot_importable
ensure_dobot_importable()

# Ensure project-level modules are importable (if this file is run from elsewhere)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import DobotDllType as dType
from scenarios.scenario_sync import scenario_sync_test  # (unused in current code)


# ===============================
#       Configuration & Paths
# ===============================
# Use the current virtualenv's Python for any subprocess calls
python_exe = str(VENV_PYTHON)

# Scenario scripts (renamed SDK folder lives at project root as "Python project")
scenario_async_rail = str(PROJECT_ROOT / "Python_project" / "scenarios" / "scenario_async_rail.py")
scenario_async_conv = str(PROJECT_ROOT / "Python_project" / "scenarios" / "scenario_async_conv.py")

# Homing scripts
homing_rail = str(PROJECT_ROOT / "Python_project" / "Home_rail.py")
homing_conv = str(PROJECT_ROOT / "Python_project" / "Home_conv.py")

p_rail = None
p_conv = None
CREATE_NEW_PROCESS_GROUP = subprocess.CREATE_NEW_PROCESS_GROUP


# ===============================
#          Function defs
# ===============================

def launch_scenario(mode: str) -> None:
    """Launch scenario processes based on the given mode ("async" supported)."""
    global p_rail, p_conv
    print(f"▶️ Launching scenario: {mode}")

    if mode == "sync":
        print("Not available for now")

    elif mode == "async":
        # Rail
        p_rail = subprocess.Popen(
            [python_exe, "-u", scenario_async_rail],
            creationflags=CREATE_NEW_PROCESS_GROUP,
        )

        # Conveyor
        p_conv = subprocess.Popen(
            [python_exe, "-u", scenario_async_conv],
            creationflags=CREATE_NEW_PROCESS_GROUP,
        )


def launch_homing() -> None:
    """Start both homing scripts and wait for completion."""
    print("🚀 [DEBUG] launch_homing called")
    try:
        p1 = subprocess.Popen([python_exe, "-u", homing_rail], creationflags=CREATE_NEW_PROCESS_GROUP)
    except Exception as e:
        print(f"❌ Error while homing the rail: {e}")
        return

    try:
        p2 = subprocess.Popen([python_exe, "-u", homing_conv], creationflags=CREATE_NEW_PROCESS_GROUP)
    except Exception as e:
        print(f"❌ Error while homing the conveyor: {e}")
        return

    p1.wait()
    p2.wait()
    print("✅ Both Dobots finished their homing.")


def dobot_emergency_stop(api) -> None:
    """Perform a DLL-level emergency stop for the given Dobot API handle."""
    global suction_state
    print("🚨 Dobot emergency stop (DLL) triggered")
    try:
        dType.SetEndEffectorParamsEx(api, 59.7, 0, 0)  # reset end effector params
        dType.SetEndEffectorSuctionCup(api, 0, 1)      # ⛔ stop suction immediately
        suction_state = False                          # update internal state
        dType.SetQueuedCmdClear(api)
        dType.SetQueuedCmdStopExec(api)
        print("✅ Suction disabled (logic).")
    except Exception as e:
        print(f"⚠️ Error during emergency stop: {e}")


def emergency_stop() -> None:
    """
    Send CTRL_BREAK to running scenario child processes and wait for clean shutdown;
    if a process does not respond, force-kill it.
    """
    global p_rail, p_conv
    print("🛑 Emergency stop requested")

    for proc in [p_rail, p_conv]:
        if proc and proc.poll() is None:
            try:
                print(f"⏹️ Sending CTRL_BREAK to process {proc.pid}")
                proc.send_signal(signal.CTRL_BREAK_EVENT)

                proc.wait(timeout=5)
                print(f"✅ Process {proc.pid} stopped cleanly")
            except subprocess.TimeoutExpired:
                proc.kill()
                print(f"⚠️ Process {proc.pid} killed forcibly")


if __name__ == "__main__":
    launch_homing()