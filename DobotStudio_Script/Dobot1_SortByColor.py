#Magician
Radioactive_Color = None
Grab_X = None
Grab_Y = None
ColorSensor_X = None
ColorSensor_Y = None
ColorSensor_Z = None
Grab_Z = None
R = None
G = None
B = None
Place_X = None
MAX = None
Place_Y = None
Place_Z = None
Place_radioactive_X = None
Place_radioactive_Y = None
Place_radioactive_Z = None
RedCount = None
GreenCount = None
BlueCount = None
Radioactive_Count = None
Non_Radioactive_Count = None

# Detect and sort the object based on color and radioactivity
def getcolor():
    global ColorSensor_X, ColorSensor_Y, ColorSensor_Z, R, G, B, MAX, Radioactive_Color
    global Place_radioactive_X, Place_radioactive_Y, Place_radioactive_Z
    global RedCount, GreenCount, BlueCount
    global Radioactive_Count, Non_Radioactive_Count
    global Place_X, Place_Y, Place_Z

    dType.SetPTPCmdEx(api, 0, ColorSensor_X, ColorSensor_Y, ColorSensor_Z, 0, 1)
    dType.dSleep(1000)

    R = dType.GetColorSensorEx(api, 0)
    G = dType.GetColorSensorEx(api, 1)
    B = dType.GetColorSensorEx(api, 2)

    dType.SetIODOEx(api, 18, 0, 1)
    MAX = max([R, G, B])

    if MAX == R:
        print("Value of red is:", R)
        if Radioactive_Color == "Red":
            print("Radioactive Red detected")
            dType.SetPTPCmdEx(api, 0, Place_radioactive_X, Place_radioactive_Y, Place_radioactive_Z, 0, 1)
            RedCount += 1
            Radioactive_Count += 1
            Sort_Radioactive()
        else:
            print("Non-Radioactive Red detected")
            dType.SetPTPCmdEx(api, 0, Place_X, Place_Y, Place_Z, 0, 1)
            RedCount += 1
            Non_Radioactive_Count += 1
            Sort_Non_Radioactive()

    elif MAX == G:
        print("Value of green is:", G)
        if Radioactive_Color == "Green":
            print("Radioactive Green detected")
            dType.SetPTPCmdEx(api, 0, Place_radioactive_X, Place_radioactive_Y, Place_radioactive_Z, 0, 1)
            GreenCount += 1
            Radioactive_Count += 1
            print("+1 Radioactive")
            Sort_Radioactive()
        else:
            print("Non-Radioactive Green detected")
            dType.SetPTPCmdEx(api, 0, Place_X, Place_Y, Place_Z, 0, 1)
            GreenCount += 1
            Non_Radioactive_Count += 1
            Sort_Non_Radioactive()

    else:
        print("Value of blue is:", B)
        if Radioactive_Color == "Blue":
            print("Radioactive Blue detected")
            dType.SetPTPCmdEx(api, 0, Place_radioactive_X, Place_radioactive_Y, Place_radioactive_Z, 0, 1)
            BlueCount += 1
            Radioactive_Count += 1
            print("+1 Radioactive")
            Sort_Radioactive()
        else:
            print("Non-Radioactive Blue detected")
            dType.SetPTPCmdEx(api, 0, Place_X, Place_Y, Place_Z, 0, 1)
            BlueCount += 1
            Non_Radioactive_Count += 1
            Sort_Non_Radioactive()

    dType.dSleep(1000)

# Sort non-radioactive objects
def Sort_Non_Radioactive():
    global Grab_X, Grab_Y, ColorSensor_Z
    dType.SetEndEffectorSuctionCupEx(api, 0, 1)
    dType.SetPTPCmdEx(api, 0, Grab_X, Grab_Y, ColorSensor_Z, 0, 1)
    STEP_PER_CIRCLE = 360.0 / 1.8 * 10.0 * 16.0
    MM_PER_CIRCLE = 3.1415926535898 * 36.0
    vel = float(30) * STEP_PER_CIRCLE / MM_PER_CIRCLE
    dType.SetEMotorEx(api, 0, 1, int(vel), 1)
    dType.dSleep(4000)
    vel = 0
    dType.SetEMotorEx(api, 0, 0, int(vel), 1)
    print("+1")

# Sort radioactive objects
def Sort_Radioactive():
    global Grab_X, Grab_Y, ColorSensor_Z
    dType.SetEndEffectorSuctionCupEx(api, 0, 1)
    dType.SetPTPCmdEx(api, 0, Grab_X, Grab_Y, ColorSensor_Z, 0, 1)
    STEP_PER_CIRCLE = 360.0 / 1.8 * 10.0 * 16.0
    MM_PER_CIRCLE = 3.1415926535898 * 36.0
    vel = float(-30) * STEP_PER_CIRCLE / MM_PER_CIRCLE
    dType.SetEMotorEx(api, 0, 1, int(vel), 1)
    dType.dSleep(3000)
    vel = 0
    dType.SetEMotorEx(api, 0, 0, int(vel), 1)
    print("+1 Radioactive")


# === Initial setup
Radioactive_Color = "Green"
Grab_X = -98
Grab_Y = -282
Grab_Z = 16
ColorSensor_X = -84
ColorSensor_Y = -196
ColorSensor_Z = 40
Place_X = 260
Place_Y = 188
Place_Z = 23
Place_radioactive_X = -100
Place_radioactive_Y = 200
Place_radioactive_Z = 23

dType.SetEndEffectorParamsEx(api, 59.7, 0, 0, 1)
RedCount = 0
BlueCount = 0
GreenCount = 0
Radioactive_Count = 0
Non_Radioactive_Count = 0
dType.SetColorSensor(api, 1, 1, 1)
dType.SetInfraredSensor(api, 1, 2, 1)

dType.dSleep(1000)
dType.SetPTPCmdEx(api, 0, Grab_X, Grab_Y, ColorSensor_Z, 0, 1)

# === Main loop
while True:
    STEP_PER_CIRCLE = 360.0 / 1.8 * 10.0 * 16.0
    MM_PER_CIRCLE = 3.1415926535898 * 36.0
    vel = float(30) * STEP_PER_CIRCLE / MM_PER_CIRCLE
    dType.SetEMotorEx(api, 1, 1, int(vel), 1)

    if dType.GetInfraredSensor(api, 2)[0] == 1:
        dType.SetEMotorEx(api, 1, 0, 0, 1)
        dType.SetEndEffectorSuctionCupEx(api, 1, 1)
        current_pose = dType.GetPose(api)
        dType.SetPTPCmdEx(api, 2, Grab_X, Grab_Y, Grab_Z, current_pose[3], 1)
        getcolor()
