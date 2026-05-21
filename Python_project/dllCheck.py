# ===============================
# File: dllCheck.py
# ===============================
"""
DLL export inspector (Windows)
------------------------------
Purpose
    Inspect a Windows DLL and list its exported functions using ``pefile``.

Notes
    - Update ``DLL_PATH`` to the absolute location of your ``DobotDll.dll``.
    - Requires the ``pefile`` package (``pip install pefile``).
"""


import pefile
from paths import PROJECT_ROOT  # + add this line

DLL_PATH = str((PROJECT_ROOT / "Python_project" / "DobotDll.dll").resolve())  # + replace the line


def list_exports(dll_path: str) -> None:
    """Load ``dll_path`` and print its exported symbols (address + name)."""
    pe = pefile.PE(dll_path)
    print("Exported functions:")
    for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        addr = hex(pe.OPTIONAL_HEADER.ImageBase + exp.address)
        name = exp.name.decode() if exp.name else "None"
        print(f"{addr}: {name}")


if __name__ == "__main__":
    list_exports(DLL_PATH)
