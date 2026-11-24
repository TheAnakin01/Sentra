"""Sentra API. Run with:  uvicorn api:app --reload
Docs page (auto-generated): http://127.0.0.1:8000/docs
"""
from typing import Optional

from fastapi import FastAPI, HTTPException

import db

app = FastAPI(title="Sentra API", description="Vehicle crossing counts")


def _resolve_run(conn, run_id: Optional[str]) -> str:
    run = run_id or db.latest_run(conn)
    if run is None:
        raise HTTPException(status_code=404, detail="No data yet. Run count.py first.")
    return run


@app.get("/runs")
def runs():
    """All processed runs, newest first."""
    conn = db.init()
    try:
        return db.list_runs(conn)
    finally:
        conn.close()


@app.get("/counts")
def counts(run_id: Optional[str] = None):
    """Totals per direction and vehicle type (latest run by default)."""
    conn = db.init()
    try:
        run = _resolve_run(conn, run_id)
        rows = conn.execute(
            "SELECT direction, vehicle_type, COUNT(*) AS count FROM crossings "
            "WHERE run_id = ? GROUP BY direction, vehicle_type ORDER BY direction, vehicle_type",
            (run,),
        ).fetchall()
        return {
            "run_id": run,
            "total": sum(r["count"] for r in rows),
            "counts": [dict(r) for r in rows],
        }
    finally:
        conn.close()


@app.get("/events")
def events(run_id: Optional[str] = None, limit: int = 100):
    """Individual crossings, oldest first."""
    if not 1 <= limit <= 1000:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 1000")
    conn = db.init()
    try:
        run = _resolve_run(conn, run_id)
        rows = conn.execute(
            "SELECT ts, video_time_s, track_id, direction, vehicle_type FROM crossings "
            "WHERE run_id = ? ORDER BY id LIMIT ?",
            (run, limit),
        ).fetchall()
        return {"run_id": run, "events": [dict(r) for r in rows]}
    finally:
        conn.close()
