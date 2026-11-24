"""Sentra dashboard. Run with:  streamlit run dashboard.py"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import db

st.set_page_config(page_title="Sentra", layout="wide")
st.title("Sentra: vehicle counts")

# colors stay the same for the same vehicle type in every chart
TYPE_COLORS = {"car": "#2a7de1", "motorcycle": "#e8833a", "bus": "#3aa655", "truck": "#8e5bd0"}
DIR_COLORS = {"toward": "#2a7de1", "away": "#e8833a"}

SAMPLE_DB = "docs/sample.db"   # small committed sample so a deployed dashboard shows something

conn = db.init()
runs = db.list_runs(conn)
using_sample = False
if not runs and Path(SAMPLE_DB).exists():
    conn.close()
    conn = db.init(SAMPLE_DB)
    runs = db.list_runs(conn)
    using_sample = True
if not runs:
    st.info("No data yet. Run `python count.py` first, then refresh this page.")
    st.stop()
if using_sample:
    st.caption("Showing the bundled sample run. Run `python count.py` to see your own data.")

run_id = st.sidebar.selectbox("Run", [r["run_id"] for r in runs])
bucket = st.sidebar.radio("Time buckets", ["second", "minute", "hour"], index=0)

df = pd.read_sql_query(
    "SELECT ts, video_time_s, track_id, direction, vehicle_type FROM crossings "
    "WHERE run_id = ? ORDER BY id",
    conn,
    params=(run_id,),
)
conn.close()
df["ts"] = pd.to_datetime(df["ts"], format="ISO8601")

# headline numbers
c1, c2, c3 = st.columns(3)
c1.metric("Total counted", len(df))
c2.metric("Toward camera", int((df["direction"] == "toward").sum()))
c3.metric("Away from camera", int((df["direction"] == "away").sum()))

left, right = st.columns(2)

by_type = df.groupby("vehicle_type").size().reset_index(name="count")
left.plotly_chart(
    px.bar(by_type, x="vehicle_type", y="count", color="vehicle_type",
           color_discrete_map=TYPE_COLORS, title="By vehicle type")
    .update_layout(showlegend=False),
    width="stretch",
)

by_dir = df.groupby("direction").size().reset_index(name="count")
right.plotly_chart(
    px.bar(by_dir, x="direction", y="count", color="direction",
           color_discrete_map=DIR_COLORS, title="By direction")
    .update_layout(showlegend=False),
    width="stretch",
)

freq = {"second": "s", "minute": "min", "hour": "h"}[bucket]
over_time = (
    df.set_index("ts").groupby([pd.Grouper(freq=freq), "vehicle_type"])
    .size().reset_index(name="count")
)
st.plotly_chart(
    px.bar(over_time, x="ts", y="count", color="vehicle_type",
           color_discrete_map=TYPE_COLORS, title=f"Counts per {bucket}"),
    width="stretch",
)

st.subheader("Annotated video")
gif = Path("docs/demo.gif")
if gif.exists():
    st.image(str(gif), caption="Detections, trails and the counting line")
else:
    st.caption("Run `python count.py --gif docs/demo.gif` to create the preview.")

with st.expander("All crossings"):
    st.dataframe(df, width="stretch")
