#Magician
import json
import os
import subprocess

#######################################################################################################
'''
THIS SCRIPT IS NOT UP TO DATE, PLEASE USE THE PYTHON VERSION OR UPDATE THIS ONE.

IT CAN ONLY WORK ON DOBOTSTUDIO APPLICATION.

'''
######################################################################################################

# === 1. Parametres Dobot ===

DROP_X = 130
DROP_Y = -177
DROP_Z = -60
DROP_Rail = 575
LIFT_Z = DROP_Z + 100
JSON_PATH = r"C:\Users\TOUJAN Oceam\Documents\CentraleSupelec\Voyage Norvege\Work\positions_robot.json"


# Rail activation and effector parameters
dType.SetIODOEx(api, 18, 1, 1)
dType.SetEndEffectorParamsEx(api, 59.7, 0, 0, 1)

def load_next_component():
    if not os.path.exists(JSON_PATH):
        print("File not found.")
        return None

    with open(JSON_PATH, "r") as f:
        data = json.load(f)

    if len(data["components"]) == 0:
        return None

    comp = data["components"].pop(0)

    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=2)

    return comp

def pick_and_place(comp):
    grab_x, grab_y, grab_z = comp["x"], comp["y"], -25
    rail_pos = 575

    current_pose = dType.GetPose(api)
    dType.SetPTPWithLCmdEx(api, 1, current_pose[0], current_pose[1], current_pose[2], current_pose[3], 0, 1) #  move the rail 0
    current_pose = dType.GetPose(api)
    dType.SetPTPCmdEx(api, 2, grab_x, grab_y, LIFT_Z, current_pose[3], 1) #go above a cube

    current_pose = dType.GetPose(api)
    dType.SetPTPCmdEx(api, 2, grab_x, grab_y, grab_z, current_pose[3], 1) #take the cube
    dType.SetEndEffectorSuctionCupEx(api, 1, 1)

    current_pose = dType.GetPose(api)
    dType.SetPTPCmdEx(api, 2, grab_x, grab_y, LIFT_Z, current_pose[3], 1) #raise the cube


    current_pose = dType.GetPose(api)
    dType.SetPTPWithLCmdEx(api, 1, current_pose[0], current_pose[1], current_pose[2], current_pose[3], rail_pos, 1)#go to rail pos
	
    current_pose = dType.GetPose(api)
    dType.SetPTPCmdEx(api, 2, DROP_X, DROP_Y, LIFT_Z, current_pose[3], 1)

    current_pose = dType.GetPose(api)
    dType.SetPTPCmdEx(api, 2, DROP_X, DROP_Y, DROP_Z, current_pose[3], 1)
    dType.SetEndEffectorSuctionCupEx(api, 0, 1)

    current_pose = dType.GetPose(api)
    dType.SetPTPCmdEx(api, 2, DROP_X, DROP_Y, LIFT_Z, current_pose[3], 1)


# === 3. Main loop ===
while True:
    component = load_next_component()
    if component is None:
        print("No components remaining.")
        break
    print("Component :", component)
    pick_and_place(component)
