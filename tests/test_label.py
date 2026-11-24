import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from label import is_repeat, key_to_mark, load_rows, save_rows


def test_lowercase_is_toward():
    assert key_to_mark("m") == ("toward", "motorcycle")
    assert key_to_mark("c") == ("toward", "car")


def test_uppercase_is_away():
    assert key_to_mark("B") == ("away", "bus")
    assert key_to_mark("K") == ("away", "truck")


def test_other_keys_are_ignored():
    assert key_to_mark("x") is None
    assert key_to_mark("") is None
    assert key_to_mark(" ") is None


def test_save_and_load_roundtrip_sorted(tmp_path):
    path = tmp_path / "gt.csv"
    save_rows(path, [
        {"time_s": 5.0, "direction": "away", "vehicle_type": "bus"},
        {"time_s": 1.5, "direction": "toward", "vehicle_type": "car"},
    ])
    rows = load_rows(path)
    assert [r["time_s"] for r in rows] == [1.5, 5.0]
    assert rows[0]["vehicle_type"] == "car"


def test_load_missing_file_is_empty(tmp_path):
    assert load_rows(tmp_path / "nope.csv") == []


def test_held_key_is_a_repeat_but_a_later_press_is_not():
    last = {}
    assert is_repeat(last, "c", 10.0) is False
    assert is_repeat(last, "c", 10.1) is True      # key repeat
    assert is_repeat(last, "m", 10.1) is False     # different key
    assert is_repeat(last, "c", 10.6) is False     # pressed again on purpose
