from robolink import *
from robodk import *
from time import sleep

sim = robolink.Robolink()


#Items
base2 = sim.Item("Dobot Magician2 Base")
robot2 = sim.Item("Dobot Magician2")
tool2  = sim.Item("Vacuum Gripper2")

conveyor1 = sim.Item("Conveyor_1")
conveyor2 = sim.Item("Conveyor_2")

box1 = sim.Item("Yellow_Cube")
box2= sim.Item("Red_Cube")
box3 = sim.Item("Green_Cube")
box4 = sim.Item("Blue_Cube")

# Frames
box_Frame_Pick = sim.Item("Conveyor1_Frame")
box_Frame_Put = sim.Item("Conveyor2_Frame") 
put_Conveyor2_Frame = sim.Item("Put_Conveyor2_Frame", ITEM_TYPE_FRAME)  

# Targets
home2_Pick = sim.Item("Home2_Pick")
app_Pick2_Pos = sim.Item("App_Pick2_Pos")
pick2_Pos = sim.Item("Pick2_Pos")

sensor_Place2_Pos = sim.Item("Sensor_Place2_Pos")

app_Place2_Pos = sim.Item("App_Place2_Pos")
place2_Pos = sim.Item("Place2_Pos")


# Gå to the conveyor and pick the cube
robot2.setSpeed(200,50)
robot2.setTool(tool2)
robot2.setFrame(base2)

# Go home
robot2.MoveJ(home2_Pick)

# Pick
robot2.MoveJ(app_Pick2_Pos)
robot2.MoveJ(pick2_Pos)
tool2.AttachClosest()
robot2.MoveJ(app_Pick2_Pos)

# check the colour of the Cube
robot2.MoveJ(sensor_Place2_Pos)
sleep(0.2)

# go to put position
robot2.MoveJ(app_Place2_Pos)
robot2.MoveJ(place2_Pos)
tool2.DetachAll()
box1.setParent(put_Conveyor2_Frame)

robot2.MoveJ(app_Place2_Pos)

robot2.MoveJ(home2_Pick)