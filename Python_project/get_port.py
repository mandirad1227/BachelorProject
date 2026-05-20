"""
Serial port helpers for Dobot roles
-----------------------------------
Purpose
    Associate logical roles ("convoyeur", "rail") with fixed Windows COM ports,
    and provide a small utility to print all available ports for debugging.

Functions
    - check_all_ports(): Print all discovered serial ports and their metadata.
    - get_port(role="rail"): Return the COM port string for the given logical role.

Notes
    - Update `DOBOT_ROLES` to match your system (Windows Device Manager).
    - The `DobotDllType` import is kept for parity with the original environment.
"""

# ===============================
#              Imports
# ===============================
import serial.tools.list_ports
import DobotDllType as dType  # kept for parity with original, even if not used directly here


# ===============================
#       Configuration & State
# ===============================
# Roles associated with fixed COM ports (set manually in Windows)
DOBOT_ROLES = {
    "convoyeur": "COM3",
    "rail": "COM5",
}


# ===============================
#          Function defs
# ===============================

def check_all_ports() -> None:
    """Print all active COM ports and useful metadata (debug helper)."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        print("Port:", port.device)
        print("Serial number:", port.serial_number)
        print("VID:PID:", port.vid, port.pid)
        print("HWID:", port.hwid)


def get_port(role: str = "rail") -> str:
    """Return the COM port string for the given logical role."""
    if role not in DOBOT_ROLES:
        raise RuntimeError(f"❌ No COM port defined for role: {role}")

    port = DOBOT_ROLES[role]
    print(f"🔌 Port for {role}: {port}")
    return port


# Optional manual test
# if __name__ == "__main__":
#     check_all_ports()
#     print(get_port("rail"))
#     print(get_port("convoyeur"))