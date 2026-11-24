"""SQLite helpers for Sentra. One table: every line crossing is one row."""
import sqlite3
from pathlib import Path

DB_PATH = "data/sentra.db"


def connect(path=None):
    path = path or DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init(path=None):
    conn = connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS crossings (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id       TEXT NOT NULL,
            ts           TEXT NOT NULL,      -- ISO time of the crossing
            video_time_s REAL NOT NULL,      -- seconds since the video started
            track_id     INTEGER NOT NULL,
            direction    TEXT NOT NULL,      -- 'toward' or 'away'
            vehicle_type TEXT NOT NULL       -- car, motorcycle, bus, truck
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_run ON crossings(run_id)")
    conn.commit()
    return conn


def insert_crossing(conn, run_id, ts, video_time_s, track_id, direction, vehicle_type):
    conn.execute(
        "INSERT INTO crossings (run_id, ts, video_time_s, track_id, direction, vehicle_type)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (run_id, ts, video_time_s, track_id, direction, vehicle_type),
    )


def latest_run(conn):
    row = conn.execute("SELECT run_id FROM crossings ORDER BY id DESC LIMIT 1").fetchone()
    return row["run_id"] if row else None


def list_runs(conn):
    rows = conn.execute(
        "SELECT run_id, COUNT(*) AS n FROM crossings GROUP BY run_id ORDER BY MAX(id) DESC"
    ).fetchall()
    return [dict(r) for r in rows]
