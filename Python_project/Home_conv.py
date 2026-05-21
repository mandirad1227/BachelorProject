"""
Homing sequence for the conveyor Dobot
--------------------------------------
Purpose
    Connect to the conveyor Dobot, move to a safe pose, issue a HOME command,
    wait for completion, then disconnect cleanly. Provides a SIGTERM handler to
    trigger a safe emergency stop if the process is terminated.

Functions
    - handle_sigterm(signum, frame): Emergency stop handler; uses global `api_conv`.
    - run_homing_conv(): Connect → queue start → safe pose → HOME → wait → disconnect.

Notes
    - Requires the Dobot SDK (`DobotDllType.py` + `DobotDll.dll`) to be importable.
    - COM ports are resolved by `get_port()`.
    - Logic preserved from the original script; only wording/structure improved.
"""

# ===============================
#              Imports
# ===============================
import sys
import signal
import time
import traceback
from pathlib import Path
_root = Path(__file__).resolve().parent
for _ in range(6):  # goes up to 6 levels if needed
    if (_root / "paths.py").exists():
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        break
    _root = _root.parent
# --------------------------------------------------------------------------

# Make the project root & Dobot SDK available without hardcoded paths
from paths import PROJECT_ROOT, ensure_dobot_importable
ensure_dobot_importable()  # add SDK dir to sys.path and DLL search path (Windows)

# Ensure project-level modules (get_port, launcher, …) are importable when running from subfolders
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Now these imports succeed regardless of where you launch the script from
import DobotDllType as dType
from get_port import get_port
from launcher import dobot_emergency_stop


# ===============================
#          Function defs
# ===============================
api_conv = None  # Global API handle used by the signal handler


def handle_sigterm(signum, frame) -> None:
    """Emergency stop on SIGTERM: stop safely and disconnect."""
    print("🛑 SIGTERM received, emergency stop for Dobot Conveyor")
    if api_conv:
        try:
            dobot_emergency_stop(api_conv)
            dType.DisconnectDobot(api_conv)
        except Exception as e:
            print(f"⚠️ Error during emergency stop: {e}")
    sys.exit(0)


# Register the signal handler (done at import time as in the original)
signal.signal(signal.SIGTERM, handle_sigterm)


def run_homing_conv() -> None:
    """
    Run the conveyor Dobot homing sequence.

    Steps:
        1) Load the DLL and connect to the conveyor Dobot.
        2) Start the queued command execution.
        3) Move to a safe pose.
        4) Issue the HOME command (queued) and wait ~15 s.
        5) Stop queue and disconnect in `finally`.
    """
    global api_conv
    try:
        api_conv = dType.load()
        port_conv = get_port("convoyeur")
        state_conv = dType.ConnectDobot(api_conv, port_conv, 115200)

        dType.SetQueuedCmdStartExec(api_conv)
        pose = dType.GetPose(api_conv)
        dType.SetPTPCmdEx(api_conv, 2, pose[0], pose[1], 50, 0, 1)  # safe pose before homing
        dType.SetHOMECmd(api_conv, temp=0, isQueued=1)
        time.sleep(15)

        print("✅ Homing completed. Disconnecting…")

    except Exception as e:
        print("❌ Error during conveyor initialization:", e)
        traceback.print_exc()

    finally:
        if api_conv:
            try:
                dType.SetQueuedCmdStopExec(api_conv)
                dType.DisconnectDobot(api_conv)
                print("✅ Clean disconnection completed.")
            except Exception:
                pass


# Run only when executed directly
if __name__ == "__main__":
    run_homing_conv()