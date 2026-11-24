import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import db
from api import app


def _use_temp_db(tmp_path, monkeypatch, rows):
    path = str(tmp_path / "test.db")
    conn = db.init(path)
    for r in rows:
        db.insert_crossing(conn, *r)
    conn.commit()
    conn.close()
    monkeypatch.setattr(db, "DB_PATH", path)


def test_counts_group_by_direction_and_type(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch, [
        ("run-1", "2026-01-01T00:00:01", 1.0, 1, "toward", "car"),
        ("run-1", "2026-01-01T00:00:02", 2.0, 2, "toward", "car"),
        ("run-1", "2026-01-01T00:00:03", 3.0, 3, "away", "bus"),
    ])
    r = TestClient(app).get("/counts")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert {"direction": "toward", "vehicle_type": "car", "count": 2} in body["counts"]


def test_empty_database_gives_404(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch, [])
    assert TestClient(app).get("/counts").status_code == 404


def test_events_limit_is_validated(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch, [("run-1", "2026-01-01T00:00:01", 1.0, 1, "toward", "car")])
    assert TestClient(app).get("/events?limit=0").status_code == 422
