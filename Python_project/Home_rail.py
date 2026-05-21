"""
Homing sequence for the rail Dobot
----------------------------------
Purpose
    Connect to the rail Dobot, enable the linear rail, issue a HOME command,
    wait for completion, then disconnect cleanly. Provides a SIGTERM handler to
    trigger a safe emergency stop if the process is terminated.

Functions
    - handle_sigterm(signum, frame): Emergency stop handler; uses global `api_rail`.
    - run_homing_rail(): Connect → enable rail → queue start → HOME → wait → disconnect.

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
api_rail = None  # Global API handle used by the signal handler


def handle_sigterm(signum, frame) -> None:
    """Emergency stop on SIGTERM: stop safely and disconnect."""
    print("🛑 SIGTERM received, emergency stop for Dobot Rail")
    if api_rail:
        try:
            dobot_emergency_stop(api_rail)
            dType.DisconnectDobot(api_rail)
        except Exception as e:
            print(f"⚠️ Error during emergency stop: {e}")
    sys.exit(0)


# Register the signal handler (done at import time as in the original)
signal.signal(signal.SIGTERM, handle_sigterm)


def run_homing_rail() -> None:
    """
    Run the rail Dobot homing sequence.

    Steps:
        1) Load the DLL and connect to the rail Dobot.
        2) Enable the linear rail via `SetDeviceWithL`.
        3) Start the queued command execution.
        4) Issue the HOME command (queued) and wait ~20 s.
        5) Stop queue and disconnect in `finally`.
    """
    global api_rail
    try:
        api_rail = dType.load()
        port_rail = get_port("rail")
        state_rail = dType.ConnectDobot(api_rail, port_rail, 115200)

        dType.SetDeviceWithL(api_rail, 1, 0)  # enable rail
        dType.SetQueuedCmdStartExec(api_rail)
        dType.SetHOMECmd(api_rail, temp=0, isQueued=1)
        time.sleep(20)

        print("✅ Homing completed. Disconnecting…")

    except Exception as e:
        print("❌ Error during rail initialization:", e)
        traceback.print_exc()

    finally:
        if api_rail:
            try:
                dType.SetQueuedCmdStopExec(api_rail)
                dType.DisconnectDobot(api_rail)
                print("✅ Clean disconnection completed.")
            except Exception:
                pass


# Run only when executed directly
if __name__ == "__main__":
    run_homing_rail()