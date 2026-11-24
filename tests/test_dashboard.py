import os
import shutil
import sys

from streamlit.testing.v1 import AppTest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

import db


def test_dashboard_handles_timestamps_with_and_without_fractions(tmp_path, monkeypatch):
    """A crossing that lands on a whole second has no '.ffffff' part. Mixed formats must not crash."""
    for name in ("dashboard.py", "db.py"):
        shutil.copy(os.path.join(ROOT, name), tmp_path / name)
    monkeypatch.chdir(tmp_path)

    conn = db.init("data/sentra.db")
    db.insert_crossing(conn, "run-1", "2026-01-01T10:00:00", 0.0, 1, "toward", "car")
    db.insert_crossing(conn, "run-1", "2026-01-01T10:00:01.500000", 1.5, 2, "toward", "bus")
    conn.commit()
    conn.close()

    at = AppTest.from_file(str(tmp_path / "dashboard.py"), default_timeout=60).run()
    assert not at.exception
    assert [m.value for m in at.metric][0] == "2"


def test_dashboard_without_any_data_shows_a_message(tmp_path, monkeypatch):
    for name in ("dashboard.py", "db.py"):
        shutil.copy(os.path.join(ROOT, name), tmp_path / name)
    monkeypatch.chdir(tmp_path)
    at = AppTest.from_file(str(tmp_path / "dashboard.py"), default_timeout=60).run()
    assert not at.exception
    assert any("No data yet" in i.value for i in at.info)
