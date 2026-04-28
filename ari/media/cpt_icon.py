import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Create figure and axis
fig, ax = plt.subplots(1, 1, figsize=(0.15, 0.15))

# Define triangle vertices (2x smaller, upside down)
triangle = np.array(
    [
        [0.5, 0.4742],  # bottom point
        [0.4825, 0.51515],  # top left
        [0.5175, 0.51515],  # top right
        [0.5, 0.4742],
    ]
)  # close the triangle

# Draw and fill the triangle
ax.fill(triangle[:, 0], triangle[:, 1], "k", linewidth=1.125)

# Draw a horizontal line through the triangle (centered vertically)
ax.plot([0.4825, 0.5175], [0.4947, 0.4947], "k-", linewidth=1.5)

# Set equal aspect ratio and remove axes
ax.set_aspect("equal")
ax.axis("off")
ax.set_xlim(0.47, 0.53)
ax.set_ylim(0.47, 0.53)
# ax.set_xlim(0.4805, 0.5195)
# ax.set_ylim(0.472, 0.517)
# plt.show()
# Save the icon
plt.tight_layout()
plt.savefig(
    "triangle_icon.png", dpi=300, bbox_inches="tight", pad_inches=0, transparent=True
)
print("Triangle icon created successfully!")
plt.close()
