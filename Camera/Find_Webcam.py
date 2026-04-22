# ===============================
# File: Find_Webcam.py
# ===============================
"""
Camera index probe utility
--------------------------
Purpose
    Try opening a series of camera indices and print which ones are available.
Usage
    Run the script; by default it probes indices 0..4.
"""

import cv2
import subprocess
from typing import List, Optional
# --------- Listing des caméras (Windows) ---------
def list_ds_cameras() -> List[str]:
    """
    Retourne la liste des caméras DirectShow par leur 'friendly name'.
    Nécessite PowerShell (présent par défaut sur Windows).
    """
    try:
        ps_cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            r"(Get-CimInstance Win32_PnPEntity | Where-Object {$_.Service -eq 'usbvideo'} | Select-Object -ExpandProperty Name) -join [Environment]::NewLine"
        ]
        out = subprocess.check_output(ps_cmd, stderr=subprocess.STDOUT, encoding="utf-8", timeout=5)
        names = [line.strip() for line in out.splitlines() if line.strip()]
        return names
    except Exception:
        # Fallback vide si PowerShell indispo
        return []

def find_available_cameras(max_index: int = 5) -> list[int]:
    """Return a list of camera indices that can be opened."""
    print("Searching for available cameras…")
    found: list[int] = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"✅ Camera found at index {i}")
            found.append(i)
            cap.release()
        else:
            print(f"❌ No camera at index {i}")
    return found


if __name__ == "__main__":
    find_available_cameras()
    print("Cams:", list_ds_cameras())
