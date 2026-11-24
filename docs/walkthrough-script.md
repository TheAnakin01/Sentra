# Sentra walkthrough: script for a 3-minute video

Record your screen while you talk. Speak in your own words; these are prompts, not lines to read.

**0:00 The problem (20 s)**
- Show the demo GIF or a few seconds of the annotated video.
- Say what Sentra does: counts vehicles crossing a line, by direction and type.

**0:20 Detection and tracking (40 s)**
- Run `python count.py --show`.
- Explain: detection answers "what is in this frame?", tracking answers "is this the same vehicle as before?". Point at an ID and its trail.
- Mention why nano and why only four vehicle classes.

**1:00 Counting (40 s)**
- Open `counting.py` (it is 10 lines).
- Explain the rule: previous position vs current position vs the line. Each ID is counted once, which is why the `counted` set exists.
- Mention that the line position matters, and that you chose it by looking at where vehicles are large and tracked steadily.

**1:40 Storage, API, dashboard (40 s)**
- Show `data/sentra.db` rows in the API page (`/docs`, then `/counts`).
- Show the dashboard charts: by type, by direction, over time.

**2:20 Accuracy and failures (30 s)**
- Show the `evaluate.py` output with your real numbers (only after you have measured them).
- Show one failure case honestly: the rickshaw labelled "truck", or the ghost detections, and say what you would do next (fine-tune on Indian vehicle types).

**2:50 Close (10 s)**
- Link to the GitHub repo.

## Questions to be ready for in an interview

- Why can't detection alone count vehicles?
- What happens if the tracker changes a vehicle's ID in the middle of the frame?
- Why did you pick this line position, and how would you choose it for a new camera?
- What are precision and recall here, and which matters more for traffic counting?
- What would you change to run this on a live camera instead of a file?
