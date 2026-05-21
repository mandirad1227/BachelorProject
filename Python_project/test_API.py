import DobotDllType as dType
import time
import ctypes
from get_port import get_port
import DobotDllType as dType

try : 
    api = dType.load()
    port_conv = get_port("convoyeur")
    state_conv = dType.ConnectDobot(api, port_conv, 115200)
except Exception as e :
    print("problem :", e)

dType.SetQueuedCmdClear(api)
dType.SetQueuedCmdStartExec(api)

# Rail
def test_rail():
    dType.SetDeviceWithL(api, 1, 0)

    print("Rail activé ? →", dType.GetDeviceWithL(api)[0])  # Doit être 1
    # Activation du rail et parametres de l'effecteur
    dType.SetIODOEx(api, 18, 1, 1)
    # Ensuite tu fais un homing
    dType.SetHOMEParams(api, 250, 0, 50, 0)
    dType.SetHOMECmd(api, 0, isQueued=1)
    dType.SetQueuedCmdStartExec(api)

    # dType.SetPTPCommonParams(api, 100, 100)
    # dType.SetPTPWithLCmd(api, 1, 200, 0, 0, 0, 0)
    # time.sleep(1)
    # dType.SetPTPWithLCmd(api, 1, 200, 0, 0, 0, 650)

    # time.sleep(3)
# Convoyeur
def test_convoyeur():
    print("Test: Forward 5s")
    dType.SetEMotor(api, 0, 1, 5000)
    time.sleep(5)

    print("Stop")
    dType.SetEMotor(api, 0, 0, 0)
    time.sleep(1)

    print("Test: Reverse 5s")
    dType.SetEMotor(api, 1, 1, -5000)
    time.sleep(5)

    print("Stop")
    dType.SetEMotor(api, 1, 0, 0)

# Capteur IR
def test_capteur_ir():
    print("IR:", dType.GetInfraredSensor(api, 0)[0])

# Capteur lumière
def test_capteur_lumiere():
    print("Lumière:", dType.GetColorSensor(api)[0])
    dType.SetHOMECmd(api, 0, isQueued=1)
    dType.SetQueuedCmdStartExec(api)

# ⬇️ Décommente une seule ligne à la fois
# test_rail()
test_convoyeur()
# test_capteur_ir()
# test_capteur_lumiere()

dType.SetQueuedCmdStopExec(api)
dType.DisconnectDobot(api)
from ctypes import windll
windll.kernel32.FreeLibrary.argtypes = [ctypes.c_void_p]
windll.kernel32.FreeLibrary(api._handle)
