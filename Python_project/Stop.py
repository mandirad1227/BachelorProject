import traceback
from dobot_connection import get_api
import DobotDllType as dType

def emergency_stop_rail(api):
    # 1. Arrêt immédiat des commandes en file
    dType.SetQueuedCmdForceStopExec(api)

    dType.SetEndEffectorSuctionCup(api, 0, 0)  # coupe la ventouse

def emergency_stop_conv(api):
    # 1. Arrêt immédiat des commandes en file
    dType.SetQueuedCmdForceStopExec(api)

    # 2. Arrêt de tous les moteurs (bras + rail)
    dType.SetEMotor(api, index=0, isEnabled=0, speed=0)
    dType.SetEMotor(api, index=1, isEnabled=0, speed=0)

    # 3. Coupure de la ventouse
    dType.SetEndEffectorSuctionCup(api, enableCtrl=0, on=0)


try:
    print("🛑 Emergency stop triggered !")

    api_conv, port_conv, baudrate_conv= get_api("convoyeur")
    state_conv = dType.ConnectDobot(api_conv, port_conv, baudrate_conv)[0]
    emergency_stop_conv(api_conv)
    dType.SetQueuedCmdStopExec(api_conv)

    print("🛑 Dobot on rail is off")

    api_rail, port_rail, baudrate_rail= get_api("rail")
    state_rail = dType.ConnectDobot(api_rail, port_rail, baudrate_rail)[0]
    emergency_stop_rail(api_rail)
    dType.SetQueuedCmdStopExec(api_rail)

    print("🛑 Dobot with conveyor is off")

except KeyboardInterrupt:
    print(f"⚠️ Keyboard interrupt")

except Exception as e :
    print("❌ Erreur lors de l'initialisation :", e)
    traceback.print_exc()