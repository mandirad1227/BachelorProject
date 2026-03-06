
# Link to RoboDK
#### Dobot1 Programme ####

from robolink import *   
from robodk import * 
from time import sleep
sim = robolink.Robolink()

#Items
base = sim.Item("Dobot Magician1 Base")
robot1 = sim.Item("Dobot Magician1")
tool1 = sim.Item("Vacuum Gripper1")


#Conveyors
conveyor1 = sim.Item("Conveyor Belt1")

#frames
baseFrame = sim.Item("Dobot Magician1 Base")
rail = sim.Item("Linear Rail", ITEM_TYPE_ROBOT)
pickFrame =sim.Item("Box_Frame")
putFrame  = sim.Item("Put_Conveyor1_Frame")
conveyor1_Frame = sim.Item("Conveyor1_Frame")

# Targets
home1_Pick = sim.Item("Home1_Pick")
home1_Place = sim.Item("Home1_Place")
pick1_Pos = sim.Item("Pick1_Pos").Pose()
place1_Pos = sim.Item("Place1_Pos").Pose()

#objects
box1 = sim.Item("Yellow_Cube")
box2= sim.Item("Red_Cube")
box3 = sim.Item("Green_Cube")
box4 = sim.Item("Blue_Cube")
conveyor_Frame = sim.Item("Conveyro_Box_Frame")

# Targets (RAIL)

rail_home  = sim.Item("Rail_Home")
rail_pick  = sim.Item("Rail_Pick_Pos")
rail_place = sim.Item("Rail_Place_Pos")

# Approach Positoins for save movement

#app_Pick1_Pos = pick1_Pos* transl(0,0,20) 
#app_Place1_Pos = place1_Pos* transl(0,0,20) 

robot1.setSpeed(200,50)
robot1.setPoseTool(tool1)

robot1.setPoseFrame(baseFrame)
rail.MoveJ(rail_pick)

#Pick
robot1.setPoseFrame(pickFrame)
box1.setParentStatic(pickFrame)

robot1.MoveJ(home1_Pick)
#robot1.MoveJ(app_Pick1_Pos)
robot1.MoveJ(pick1_Pos)

tool1.AttachClosest()

#robot1.MoveJ(app_Pick1_Pos)
robot1.MoveJ(home1_Pick)


#Move to Put
robot1.setPoseFrame(baseFrame)
rail.MoveJ(rail_place)

#Put
robot1.setPoseFrame(putFrame)

robot1.MoveJ(home1_Place)
#robot1.MoveJ(app_Place1_Pos)
robot1.MoveJ(place1_Pos)

tool1.DetachAll()

box1.setParentStatic(putFrame)
sleep(0.2)

robot1.MoveJ(home1_Place)

robot1.setPoseFrame(conveyor1_Frame)
rail.MoveJ(rail_home)