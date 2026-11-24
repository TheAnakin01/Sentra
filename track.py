import numpy as np
from collections import defaultdict

trails = defaultdict(list)   # id -> list of recent center points

import cv2
from ultralytics import YOLO

model = YOLO("yolo11n.pt")
cap = cv2.VideoCapture("traffic.mp4")

VEHICLES = [2, 3, 5, 7]   # car, motorcycle, bus, truck

while True:
    ok, frame = cap.read()
    if not ok:
        break

    results = model.track(
        frame,
        persist=True,
        tracker="bytetrack.yaml",
        classes=VEHICLES,
        conf=0.4,
    )
    annotated = results[0].plot()
    boxes = results[0].boxes
    if boxes.id is not None:
        ids = boxes.id.int().tolist()
        centers = boxes.xywh.tolist()        # x, y, width, height per box
        for track_id, (x, y, w, h) in zip(ids, centers):
            trail = trails[track_id]
            trail.append((int(x), int(y)))
            trails[track_id] = trail[-30:]   # keep only the last 30 points
            pts = np.array(trails[track_id], dtype=np.int32).reshape(-1, 1, 2)
            cv2.polylines(annotated, [pts], False, (0, 255, 255), 2)

    annotated = cv2.resize(annotated, (960, 540))
    cv2.imshow("Sentra", annotated)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()