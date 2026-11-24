"""Compare Sentra's counts with a hand-counted ground truth.

1. Watch your clip and write one row per vehicle crossing the line in
   data/ground_truth.csv with these columns:
       time_s,direction,vehicle_type
       1.4,toward,motorcycle
       2.2,toward,car
   (time_s = seconds from the start of the video; direction = toward or away)
2. Run:  python evaluate.py            (latest run)
         python evaluate.py --run-id run-20261123-162149 --tolerance 2.0
"""
import argparse

import pandas as pd

import db


def match_events(truth: pd.DataFrame, system: pd.DataFrame, tolerance: float):
    """Pair each true crossing with the closest unused system crossing of the same
    direction and vehicle type within `tolerance` seconds. Returns (tp, fn, fp)."""
    used = set()
    tp, fn = [], []
    for _, t in truth.sort_values("time_s").iterrows():
        pool = system[
            (system["direction"] == t["direction"])
            & (system["vehicle_type"] == t["vehicle_type"])
            & (~system.index.isin(used))
        ]
        if pool.empty:
            fn.append(t)
            continue
        gaps = (pool["video_time_s"] - t["time_s"]).abs()
        best = gaps.idxmin()
        if gaps[best] <= tolerance:
            used.add(best)
            tp.append((t, system.loc[best]))
        else:
            fn.append(t)
    fp = system[~system.index.isin(used)]
    return tp, fn, fp


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", default=None)
    p.add_argument("--truth", default="data/ground_truth.csv")
    p.add_argument("--tolerance", type=float, default=2.0,
                   help="max seconds between a true and a system crossing to match")
    p.add_argument("--db", default=db.DB_PATH)
    args = p.parse_args()

    conn = db.init(args.db)
    run_id = args.run_id or db.latest_run(conn)
    if run_id is None:
        raise SystemExit("No system data. Run count.py first.")
    system = pd.read_sql_query(
        "SELECT video_time_s, direction, vehicle_type FROM crossings WHERE run_id = ?",
        conn, params=(run_id,))
    conn.close()

    try:
        truth = pd.read_csv(args.truth)
    except FileNotFoundError:
        raise SystemExit(f"{args.truth} not found. See the top of evaluate.py for the format.")
    missing = {"time_s", "direction", "vehicle_type"} - set(truth.columns)
    if missing:
        raise SystemExit(f"{args.truth} is missing columns: {sorted(missing)}")

    tp, fn, fp = match_events(truth, system, args.tolerance)
    n_truth, n_sys = len(truth), len(system)
    precision = len(tp) / n_sys if n_sys else 0.0
    recall = len(tp) / n_truth if n_truth else 0.0
    count_error = abs(n_sys - n_truth) / n_truth * 100 if n_truth else float("nan")

    print(f"Run: {run_id}   tolerance: {args.tolerance}s")
    print(f"Hand count: {n_truth}   System count: {n_sys}   Count error: {count_error:.1f}%")
    print(f"Correct (TP): {len(tp)}   Missed (FN): {len(fn)}   Extra (FP): {len(fp)}")
    print(f"Precision: {precision:.2f}   Recall: {recall:.2f}")

    if fn:
        print("\nMissed crossings (add these to your failure cases):")
        for t in fn:
            print(f"  t={t['time_s']}s {t['direction']} {t['vehicle_type']}")
    if len(fp):
        print("\nExtra system crossings (false alarms or wrong type):")
        for _, s in fp.iterrows():
            print(f"  t={s['video_time_s']}s {s['direction']} {s['vehicle_type']}")


if __name__ == "__main__":
    main()
