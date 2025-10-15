import math

# --- Helper Function ---

def regular_polygon(center, radius, sides):
    """Return list of points forming a regular polygon."""
    angle_step = 2 * math.pi / sides
    points = [
        (
            center[0] + radius * math.cos(i * angle_step),
            center[1] + radius * math.sin(i * angle_step)
        )
        for i in range(sides)
    ]
    return points

# --- Define Constant Obstacles ---

# (center_x, center_y, radius, sides)
obstacle_data = [
    (150, 150, 60, 4),  # Square
    (300, 200, 50, 4),  # Square
    (500, 150, 40, 5),  # Pentagon
    (650, 250, 50, 6),  # Hexagon
    (400, 400, 70, 8),  # Octagon
]

# Precompute polygons
obstacles = [regular_polygon((x, y), radius, sides) for (x, y, radius, sides) in obstacle_data]
