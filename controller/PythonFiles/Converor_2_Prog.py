
#### Conveyor1 programme ####

# To connect with the RoboDK
from robolink import *   
from robodk import * 
from time import sleep

sim = robolink.Robolink()

# Item
conveyor2 = sim.Item("Conveyor_2")
box1 = sim.Item("Yellow_Cube")
box2= sim.Item("Red_Cube")
box3 = sim.Item("Green_Cube")
box4 = sim.Item("Blue_Cube")

# Frame
conveyor2_Frame = sim.Item("Conveyor2 Frame")
conveyor2_Base = sim.Item("Conveyor2_Base")
put_Conveyor2_Frame = sim.Item("Put_Conveyor2_Frame", ITEM_TYPE_FRAME)

# Targets
put_pos = sim.Item("Put Conveyor2")
get_pos = sim.Item("Get Conveyor2")

if not conveyor2.Valid() or not box1.Valid():
    raise Exception("Items not found")

# Programme to set or atach the box ti the put_pos
# Attach cube to Put Conveyor1


def run_cycle():

    if not put_Conveyor2_Frame.Valid():
        raise Exception("Put_Conveyor2_Frame not found")
    
    # Reset conveyor position each cycle
    conveyor2.setJoints([0])

    box1.setParentStatic(put_Conveyor2_Frame)
    box1.setPose(transl(0,0,0,))

    box1.setParentStatic(conveyor2)
    sleep(0.1)

     # Move conveyor slowly
    for i in range(0,400,20):   # step size controls speed
        conveyor2.setJoints([i])
        sleep(0.05)
    print("Conveyor2 running complete")

run_cycle()
sleep(0.5)