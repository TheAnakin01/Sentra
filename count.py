"""Sentra: detect, track and count vehicles crossing a virtual line.

Usage:
    python count.py                       # headless, writes to data/sentra.db
    python count.py --show                # also show a live window (press q to quit)
    python count.py --gif docs/demo.gif   # save a short annotated GIF
"""
import argparse
from collections import defaultdict
from datetime import datetime, timedelta

import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO

import db
from counting import crossing_direction

VEHICLES = [2, 3, 5, 7]  # COCO class ids: car, motorcycle, bus, truck


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--video", default="traffic.mp4")
    p.add_argument("--model", default="yolo11n.pt")
    p.add_argument("--db", default=db.DB_PATH)
    p.add_argument("--line-y", type=float, default=0.58,
                   help="line height as a fraction of frame height")
    p.add_argument("--conf", type=float, default=None,
                   help="confidence threshold (default: Ultralytics default)")
    p.add_argument("--imgsz", type=int, default=None,
                   help="inference size (default: Ultralytics default)")
    p.add_argument("--start-s", type=float, default=0.0, help="start at this video time (seconds)")
    p.add_argument("--end-s", type=float, default=None, help="stop at this video time (seconds)")
    p.add_argument("--show", action="store_true", help="show a live window")
    p.add_argument("--gif", default=None, help="save an annotated GIF here")
    p.add_argument("--gif-every", type=int, default=3, help="keep every Nth frame in the GIF")
    return p.parse_args()


def main():
    args = parse_args()
    model = YOLO(args.model)
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise SystemExit(f"Could not open video: {args.video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    conn = db.init(args.db)
    start = datetime.now().replace(microsecond=0)
    run_id = start.strftime("run-%Y%m%d-%H%M%S")

    trails = defaultdict(list)   # id -> recent center points
    last_y = {}                  # id -> center y in the previous frame
    counted = set()              # ids already counted (each vehicle counts once)
    counts = defaultdict(int)    # (direction, vehicle type) -> count
    gif_frames = []

    track_kwargs = dict(persist=True, tracker="bytetrack.yaml", classes=VEHICLES, verbose=False)
    if args.conf is not None:
        track_kwargs["conf"] = args.conf
    if args.imgsz is not None:
        track_kwargs["imgsz"] = args.imgsz

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_idx = int(args.start_s * fps)
    first_idx = frame_idx
    if frame_idx:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    end_idx = int(args.end_s * fps) if args.end_s is not None else None

    stopped_early = False
    while True:
        if end_idx is not None and frame_idx >= end_idx:
            break
        ok, frame = cap.read()
        if not ok:
            # a failed read before the expected end usually means a damaged file
            expected_end = end_idx if end_idx is not None else total_frames
            stopped_early = frame_idx < expected_end - 5
            break

        h, w = frame.shape[:2]
        line_y = int(h * args.line_y)
        video_time = frame_idx / fps

        results = model.track(frame, **track_kwargs)
        annotated = results[0].plot()
        boxes = results[0].boxes

        if boxes.id is not None:
            ids = boxes.id.int().tolist()
            classes = boxes.cls.int().tolist()
            centers = boxes.xywh.tolist()

            for track_id, cls, (x, y, bw, bh) in zip(ids, classes, centers):
                trails[track_id].append((int(x), int(y)))
                trails[track_id] = trails[track_id][-30:]
                pts = np.array(trails[track_id], dtype=np.int32).reshape(-1, 1, 2)
                cv2.polylines(annotated, [pts], False, (0, 255, 255), 4)

                if track_id in last_y and track_id not in counted:
                    direction = crossing_direction(last_y[track_id], y, line_y)
                    if direction:
                        vtype = model.names[cls]
                        counts[(direction, vtype)] += 1
                        counted.add(track_id)
                        ts = (start + timedelta(seconds=video_time)).isoformat(timespec="microseconds")
                        db.insert_crossing(conn, run_id, ts, round(video_time, 2),
                                           track_id, direction, vtype)
                        conn.commit()
                last_y[track_id] = y

        cv2.line(annotated, (0, line_y), (w, line_y), (0, 0, 255), 6)
        text_y = 100
        for (direction, vtype), n in sorted(counts.items()):
            cv2.putText(annotated, f"{direction} {vtype}: {n}", (40, text_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.5, (255, 255, 255), 6)
            text_y += 110

        # shrink for display / GIF only, keeping the original shape
        scale = 960 / h
        small = cv2.resize(annotated, (int(w * scale), 960))

        if args.gif and frame_idx % args.gif_every == 0:
            g = cv2.resize(small, (int(small.shape[1] * 0.5), 480))
            gif_frames.append(Image.fromarray(cv2.cvtColor(g, cv2.COLOR_BGR2RGB)))

        if args.show:
            cv2.imshow("Sentra", small)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        frame_idx += 1

    cap.release()
    conn.close()
    if args.show:
        cv2.destroyAllWindows()

    if args.gif and gif_frames:
        gif_frames[0].save(args.gif, save_all=True, append_images=gif_frames[1:],
                           duration=int(1000 * args.gif_every / fps), loop=0)
        print(f"Saved GIF: {args.gif}")

    print(f"{run_id}: frames {first_idx}-{frame_idx} "
          f"({first_idx / fps:.1f}s-{frame_idx / fps:.1f}s), total counted = {sum(counts.values())}")
    print(dict(counts))
    if stopped_early:
        print(f"WARNING: the video stopped decoding at {frame_idx / fps:.1f}s, before the expected end. "
              "The file may be damaged or incomplete. Counts only cover the part that decoded.")


if __name__ == "__main__":
    main()
