"""The line-crossing rule, kept separate so it is easy to read and test."""
from typing import Optional


def crossing_direction(prev_y: float, y: float, line_y: float) -> Optional[str]:
    """Return 'toward' or 'away' if a vehicle crossed the horizontal line between
    the previous frame and this one, otherwise None.

    y grows downward in an image, so moving down the screen means moving
    toward the camera in this setup.
    """
    if prev_y < line_y <= y:
        return "toward"
    if prev_y >= line_y > y:
        return "away"
    return None
