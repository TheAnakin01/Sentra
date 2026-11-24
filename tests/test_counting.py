import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from counting import crossing_direction

LINE = 100


def test_moving_down_across_line_is_toward():
    assert crossing_direction(90, 110, LINE) == "toward"


def test_moving_up_across_line_is_away():
    assert crossing_direction(110, 90, LINE) == "away"


def test_staying_above_line_is_not_a_crossing():
    assert crossing_direction(50, 80, LINE) is None


def test_staying_below_line_is_not_a_crossing():
    assert crossing_direction(120, 150, LINE) is None


def test_landing_exactly_on_line_counts_toward():
    assert crossing_direction(90, 100, LINE) == "toward"


def test_not_moving_is_not_a_crossing():
    assert crossing_direction(100, 100, LINE) is None
