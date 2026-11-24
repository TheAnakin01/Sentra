import cv2
from ultralytics import YOLO

model = YOLO("yolo11n.pt")          # nano model, downloads on first run
cap = cv2.VideoCapture("traffic.mp4")

while True:
    ok, frame = cap.read()
    if not ok:                      # video ended
        break

    results = model(frame)          # detect objects in this frame
    annotated = results[0].plot()   # draw boxes + labels on a copy

    annotated = cv2.resize(annotated, (960, 540))
    cv2.imshow("Sentra", annotated)
    if cv2.waitKey(1) & 0xFF == ord("q"):   # press q to quit
        break

cap.release()
cv2.destroyAllWindows()