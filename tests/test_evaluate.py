import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from evaluate import match_events


def _frames(truth, system):
    t = pd.DataFrame(truth, columns=["time_s", "direction", "vehicle_type"])
    s = pd.DataFrame(system, columns=["video_time_s", "direction", "vehicle_type"])
    return t, s


def test_perfect_match():
    t, s = _frames([(1.0, "toward", "car")], [(1.2, "toward", "car")])
    tp, fn, fp = match_events(t, s, tolerance=2.0)
    assert (len(tp), len(fn), len(fp)) == (1, 0, 0)


def test_wrong_vehicle_type_is_a_miss_and_an_extra():
    t, s = _frames([(1.0, "toward", "truck")], [(1.0, "toward", "car")])
    tp, fn, fp = match_events(t, s, tolerance=2.0)
    assert (len(tp), len(fn), len(fp)) == (0, 1, 1)


def test_too_far_apart_in_time_does_not_match():
    t, s = _frames([(1.0, "toward", "car")], [(9.0, "toward", "car")])
    tp, fn, fp = match_events(t, s, tolerance=2.0)
    assert (len(tp), len(fn), len(fp)) == (0, 1, 1)


def test_one_system_event_cannot_match_two_true_events():
    t, s = _frames([(1.0, "toward", "car"), (1.5, "toward", "car")], [(1.2, "toward", "car")])
    tp, fn, fp = match_events(t, s, tolerance=2.0)
    assert (len(tp), len(fn), len(fp)) == (1, 1, 0)


def test_matching_on_direction_only_forgives_wrong_type():
    t, s = _frames([(1.0, "toward", "truck")], [(1.0, "toward", "car")])
    t = t.assign(vehicle_type="any")
    s = s.assign(vehicle_type="any")
    tp, fn, fp = match_events(t, s, tolerance=2.0)
    assert (len(tp), len(fn), len(fp)) == (1, 0, 0)
