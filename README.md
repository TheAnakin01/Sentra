# Sentra

Real-time vehicle detection, tracking and counting from road video. Every vehicle that crosses a virtual line is counted once, split by direction and vehicle type, stored in SQLite, served by a small API and shown on a dashboard.

![demo](docs/demo.gif)

## How it works

```
video -> YOLO (nano) detects -> ByteTrack gives each vehicle an ID -> line-crossing check
      -> SQLite (data/sentra.db) -> FastAPI (api.py) -> Streamlit dashboard (dashboard.py)
```

- **Detection:** Ultralytics YOLO nano, restricted to car, motorcycle, bus and truck.
- **Tracking:** ByteTrack keeps the same ID for a vehicle across frames.
- **Counting:** for each ID, compare its previous and current center against a horizontal line. A change of side is a crossing. Each ID is counted once. Direction is `toward` or `away` from the camera.
- **Storage:** one row per crossing (time, track id, direction, vehicle type).

## Setup

```
python -m venv venv
venv\Scripts\activate          # Windows
python -m pip install -r requirements.txt
```

Put a road video next to the code as `traffic.mp4` (videos and model files are not in the repo).

## Run

```
python count.py --gif docs/demo.gif   # process the video, store counts, save a preview GIF
python count.py --show                # same, with a live window (q to quit)
uvicorn api:app --reload              # API, docs at http://127.0.0.1:8000/docs
streamlit run dashboard.py            # dashboard
python evaluate.py                    # compare with hand counts (see the file for the CSV format)
```

Useful options: `--line-y 0.58` (line height as a fraction of frame height), `--conf`, `--imgsz`.

API: `GET /runs`, `GET /counts`, `GET /events?limit=100`.

## Results

**Not yet measured.** The only accuracy number that counts is one from a clip that was hand-counted before tuning. That evaluation (about 2 minutes of traffic, `evaluate.py`) is still to do.

Preliminary, on a 10-second portrait phone clip (`traffic.mp4`): the system counted 6 vehicles (5 motorcycles, 1 car), all moving toward the camera. A quick visual check of the frames also found 6 vehicles passing, but the line position was chosen by looking at this same clip, so this is a sanity check and not an accuracy figure.

## Known failure cases

- Auto-rickshaws are not a class in the COCO dataset the model learned from, so they get labelled as another vehicle (seen once as "truck") when far from the camera.
- Brief ghost detections lasting a few frames at the default confidence threshold.
- Vehicles already inside the frame when the video starts can be missed if they never cross the line after tracking begins.
- Vehicles that leave the frame sideways before reaching the line are not counted.
- A 4K frame is shrunk for the detector, so far-away vehicles are tiny and detected late.

## Roadmap

- Evaluation on a longer, busier clip with a hand-counted ground truth.
- Tune `conf` and the line position using that data.
- Fine-tune on Indian vehicle types (auto-rickshaw).
- Speed estimation, night footage.
