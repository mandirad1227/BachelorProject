import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import image as mpimg
from PIL import Image

# Data (x_max, x_min, z)
data = [
    (270, 214, -140),
    (282, 213, -130),
    (291, 211, -120),
    (304, 207, -110),
    (312, 205, -100),
    (318, 202, -90),
    (322, 197, -80),
    (327, 190, -70),
    (328, 182, -60),
    (331, 177, -50),
    (332, 163, -40),
    (334, 149, -30),
    (334, 128, -20),
    (334, 121, -16)
]

# Data separation
xmaxs = np.array([row[0] for row in data])
xmins = np.array([row[1] for row in data])
zs = np.array([row[2] for row in data])

# === 1. Tranche X-Z (Y=0)
fig1, ax1 = plt.subplots(figsize=(8, 6))
ax1.fill_betweenx(zs, xmins, xmaxs, color='orange', alpha=0.3, label="Zone atteignable (Y=0)")
ax1.plot(xmins, zs, 'orange')
ax1.plot(xmaxs, zs, 'orange')
ax1.set_xlabel("X (mm)")
ax1.set_ylabel("Z (mm)")
ax1.set_title("Tranche X-Z (Y = 0)")
ax1.grid(True)
ax1.invert_yaxis()
ax1.set_xlim(left=0)
ax1.set_ylim([-145, 0])  # ✅ Correction here

ax1.legend(loc="upper right")
ax1.xaxis.set_label_position('top')
ax1.xaxis.tick_top()

plt.tight_layout()
plt.show()

# === 2. Smoothed 3D path
theta = np.linspace(-np.pi * 3/4, np.pi * 3/4, 360)
z_interp = np.linspace(np.min(zs), np.max(zs), 100)

X, Y, Z = [], [], []

for z in z_interp:
    x_min = np.interp(z, zs, xmins)
    x_max = np.interp(z, zs, xmaxs)
    r_values = np.linspace(x_min, x_max, 60)

    for r in r_values:
        x_row = r * np.cos(theta)
        y_row = r * np.sin(theta)
        z_row = np.full_like(x_row, z)
        X.extend(x_row)
        Y.extend(y_row)
        Z.extend(z_row)

X = np.array(X)
Y = np.array(Y)
Z = np.array(Z)

fig2 = plt.figure(figsize=(10, 8))
ax2 = fig2.add_subplot(111, projection='3d')
scatter = ax2.scatter(X, Y, Z, c=Z, cmap='plasma', s=0.2, alpha=0.5)

ax2.set_xlabel("X (mm)")
ax2.set_ylabel("Y (mm)")
ax2.set_zlabel("Z (mm)")
ax2.set_title("Reachable volume by the Dobot (smoothed surface)")
ax2.set_xlim([-350, 350])
ax2.set_ylim([-350, 350])
ax2.set_zlim([0, -145])  # ✅ Ensure a complete scale
ax2.view_init(elev=30, azim=135)

# === Adding the robot to the center (0,0) in the form of a projected image ===
img_path = "DOBOT_MAGICIAN_02.png"  # ✅ path of your image
if not img_path.endswith("_resized.png"):
    img = Image.open(img_path)
    scale_factor = 0.25
    img = img.resize((int(img.width * scale_factor), int(img.height * scale_factor)))
    img.save("robot_resized.png")
    img_path = "robot_resized.png"

# Display the image on the map XY to Z = -145
img_array = mpimg.imread(img_path)
x_extent = [-60, 60]
y_extent = [-60, 60]
z_pos = -145  # position in Z

# Display of the image in the plane XY (in z bas)
ax2.plot_surface(
    *np.meshgrid(np.linspace(x_extent[0], x_extent[1], 2),
                 np.linspace(y_extent[0], y_extent[1], 2)),
    np.full((2, 2), z_pos),
    facecolors=img_array / 255,
    shade=False
)

plt.tight_layout()
plt.show()
