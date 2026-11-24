"""Hand-count helper: watch the video yourself and log every vehicle that crosses the line.

    python label.py --video traffic2.mp4 --line-y 0.6 --start-s 60 --end-s 140 --out data/gt_test.csv

Use the SAME --line-y you will give count.py, and label BEFORE you look at the
system's output, otherwise the accuracy number is not honest.

Keys (the window must be focused):
    c m b k   car, motorcycle, bus, truck crossing TOWARD the camera
    C M B K   (capital letters) the same, moving AWAY from the camera
    space     pause / play
    . and ,   step one frame forward / back (while paused)
    ] and [   jump one second forward / back
    u         undo the last mark
    Press ONCE per vehicle, when its center touches the line. Holding a key is ignored.
    q         save and quit
Marks are saved to data/ground_truth.csv right away, and loaded again if you restart.
"""
import argparse
import csv
import time
from pathlib import Path
from typing import Optional

import cv2

TYPES = {"c": "car", "m": "motorcycle", "b": "bus", "k": "truck"}
COLUMNS = ["time_s", "direction", "vehicle_type"]


def key_to_mark(ch: str) -> Optional[tuple]:
    """Map a key character to (direction, vehicle_type), or None for other keys.
    Lowercase = toward the camera, uppercase = away from the camera."""
    if len(ch) != 1:
        return None
    if ch in TYPES:
        return "toward", TYPES[ch]
    if ch.lower() in TYPES and ch.isupper():
        return "away", TYPES[ch.lower()]
    return None


def is_repeat(last_press: dict, ch: str, now: float, min_gap: float = 0.3) -> bool:
    """True if the same key was already handled less than min_gap seconds ago.
    Holding a key makes the keyboard repeat it, which would add many marks for one vehicle."""
    prev = last_press.get(ch)
    last_press[ch] = now
    return prev is not None and (now - prev) < min_gap


def load_rows(path):
    p = Path(path)
    if not p.exists():
        return []
    with p.open(newline="") as f:
        return [
            {"time_s": float(r["time_s"]), "direction": r["direction"], "vehicle_type": r["vehicle_type"]}
            for r in csv.DictReader(f)
        ]


def save_rows(path, rows):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["time_s"]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--video", default="traffic.mp4")
    p.add_argument("--out", default="data/ground_truth.csv")
    p.add_argument("--line-y", type=float, default=0.58)
    p.add_argument("--speed", type=float, default=1.0, help="playback speed, e.g. 0.5 for half speed")
    p.add_argument("--start-s", type=float, default=0.0, help="start at this video time (seconds)")
    p.add_argument("--end-s", type=float, default=None, help="stop at this video time (seconds)")
    args = p.parse_args()

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise SystemExit(f"Could not open video: {args.video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    first = int(args.start_s * fps)
    if args.end_s is not None:
        total = min(total, int(args.end_s * fps))
    delay = max(1, int(1000 / fps / args.speed))

    rows = load_rows(args.out)
    last_press = {}
    message = f"Loaded {len(rows)} marks" if rows else "Space = play/pause. See the top of label.py for keys."

    def read_at(i):
        i = max(first, min(total - 1, i))
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, f = cap.read()
        return (i, f) if ok else (i, None)

    idx, frame = read_at(first)
    paused = True

    while frame is not None:
        h, w = frame.shape[:2]
        scale = 900 / h
        view = cv2.resize(frame, (int(w * scale), 900))
        ly = int(900 * args.line_y)
        cv2.line(view, (0, ly), (view.shape[1], ly), (0, 0, 255), 2)
        status = "PAUSED" if paused else "PLAYING"
        cv2.putText(view, f"{status}  t={idx / fps:.2f}s  marks={len(rows)}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(view, message, (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        recent = ", ".join(f"{r['time_s']:.1f}" for r in sorted(rows, key=lambda r: r["time_s"])[-6:])
        cv2.putText(view, f"last marks (s): {recent}", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 200), 2)
        cv2.imshow("Sentra label", view)

        key = cv2.waitKey(30 if paused else delay) & 0xFF
        ch = chr(key) if 0 < key < 128 else ""

        if ch == "q":
            break
        elif ch == " ":
            paused = not paused
        elif ch == "u":
            if rows:
                gone = rows.pop()
                save_rows(args.out, rows)
                message = f"Undid {gone['direction']} {gone['vehicle_type']} at {gone['time_s']}s"
        elif ch in (".", ",", "]", "["):
            step = {".": 1, ",": -1, "]": round(fps), "[": -round(fps)}[ch]
            idx, nf = read_at(idx + step)
            frame = nf if nf is not None else frame
            paused = True
            continue
        else:
            mark = key_to_mark(ch)
            if mark and is_repeat(last_press, ch, time.monotonic()):
                message = "Ignored a repeated key. Press once per vehicle."
            elif mark:
                direction, vtype = mark
                rows.append({"time_s": round(idx / fps, 2), "direction": direction, "vehicle_type": vtype})
                save_rows(args.out, rows)
                message = f"Marked {direction} {vtype} at {idx / fps:.2f}s"

        if not paused:
            ok, nf = cap.read()
            if not ok or idx + 1 >= total:
                paused = True
                message = "End of video. Press q to save and quit."
            else:
                idx += 1
                frame = nf

    cap.release()
    cv2.destroyAllWindows()
    save_rows(args.out, rows)
    print(f"Saved {len(rows)} marks to {args.out}")


if __name__ == "__main__":
    main()
