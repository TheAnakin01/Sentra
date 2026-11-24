"""Sentra dashboard. Run with:  streamlit run dashboard.py"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import db

st.set_page_config(page_title="Sentra", layout="wide", initial_sidebar_state="collapsed")

# ---------------------------------------------------------------- design tokens
BG = "#0b0d10"
PANEL = "#111419"
LINE = "#1e232b"
INK = "#e6e8eb"        # primary text
INK_2 = "#9aa3ad"      # secondary text
INK_3 = "#5d6670"      # muted text, axes
GRID = "#171b21"

# fixed order, validated for this dark surface (dataviz validator, adjacent pairs)
TYPES = ["car", "motorcycle", "bus", "truck"]
TYPE_COLOR = {"car": "#3987e5", "motorcycle": "#d95926", "bus": "#199e70", "truck": "#c98500"}

# measured once on a hand-counted clip; see README "Results"
EVAL = {
    "clip": "traffic2.mp4, 60-140 s",
    "hand": 76, "system": 85,
    "dir_precision": 0.88, "dir_recall": 0.99,
    "type_precision": 0.81, "type_recall": 0.91,
}

SAMPLE_DB = "docs/sample.db"

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&display=swap');
html, body, [class*="css"], .stApp {{ background:{BG}; color:{INK}; font-family:'IBM Plex Sans',sans-serif; }}
#MainMenu, footer, header[data-testid="stHeader"] {{ display:none; }}
.block-container {{ padding:1.6rem 2.2rem 3rem; max-width:1500px; }}
.mono {{ font-family:'IBM Plex Mono',monospace; }}
.topbar {{ display:flex; justify-content:space-between; align-items:flex-end;
          border-bottom:1px solid {LINE}; padding-bottom:14px; margin-bottom:18px; }}
.brand {{ font-family:'IBM Plex Mono',monospace; font-size:20px; letter-spacing:.32em; font-weight:500; }}
.brand small {{ display:block; font-size:11px; letter-spacing:.14em; color:{INK_3}; margin-top:4px; font-weight:400; }}
.meta {{ font-family:'IBM Plex Mono',monospace; font-size:11px; color:{INK_2}; text-align:right; line-height:1.7; }}
.meta b {{ color:{INK}; font-weight:500; }}
.kpis {{ display:grid; grid-template-columns:repeat(5,1fr); border:1px solid {LINE}; margin-bottom:18px; }}
.kpi {{ padding:14px 16px; border-right:1px solid {LINE}; }}
.kpi:last-child {{ border-right:none; }}
.kpi-l {{ font-family:'IBM Plex Mono',monospace; font-size:10px; letter-spacing:.12em; color:{INK_3}; text-transform:uppercase; }}
.kpi-v {{ font-family:'IBM Plex Mono',monospace; font-size:30px; color:{INK}; margin-top:6px; font-variant-numeric:tabular-nums; }}
.kpi-s {{ font-size:11px; color:{INK_2}; margin-top:2px; }}
.sec {{ font-family:'IBM Plex Mono',monospace; font-size:10px; letter-spacing:.14em; color:{INK_3};
        text-transform:uppercase; border-top:1px solid {LINE}; padding-top:10px; margin:6px 0 4px; }}
.sec span {{ color:{INK_2}; float:right; letter-spacing:.04em; text-transform:none; }}
.row {{ display:flex; justify-content:space-between; font-family:'IBM Plex Mono',monospace; font-size:12px;
        padding:7px 0; border-bottom:1px solid {GRID}; color:{INK_2}; }}
.row b {{ color:{INK}; font-weight:500; }}
.bar {{ height:4px; background:{GRID}; margin:2px 0 10px; }}
.bar i {{ display:block; height:4px; background:{INK_2}; }}
.note {{ font-size:11px; color:{INK_3}; margin-top:8px; line-height:1.5; }}
[data-testid="stImage"] img {{ border:1px solid {LINE}; }}
[data-testid="stSidebar"] {{ background:{PANEL}; border-right:1px solid {LINE}; }}
</style>
""",
    unsafe_allow_html=True,
)


def base_layout(height):
    return dict(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Mono, monospace", size=11, color=INK_2),
        xaxis=dict(gridcolor=GRID, zeroline=False, linecolor=LINE, tickcolor=LINE, color=INK_3),
        yaxis=dict(gridcolor=GRID, zeroline=False, linecolor=LINE, tickcolor=LINE, color=INK_3),
        hoverlabel=dict(bgcolor=PANEL, bordercolor=LINE, font=dict(family="IBM Plex Mono", color=INK, size=11)),
        showlegend=False,
    )


# ---------------------------------------------------------------- data
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

with st.sidebar:
    run_id = st.selectbox("Run", [r["run_id"] for r in runs])
    bin_s = st.select_slider("Throughput bin (s)", options=[5, 10, 15, 30, 60], value=10)

df = pd.read_sql_query(
    "SELECT ts, video_time_s, track_id, direction, vehicle_type FROM crossings "
    "WHERE run_id = ? ORDER BY video_time_s",
    conn,
    params=(run_id,),
)
conn.close()
df["ts"] = pd.to_datetime(df["ts"], format="ISO8601")

total = len(df)
inbound = int((df["direction"] == "toward").sum())
outbound = int((df["direction"] == "away").sum())
t0, t1 = (df["video_time_s"].min(), df["video_time_s"].max()) if total else (0.0, 0.0)
span = max(t1 - t0, 1e-9)
rate = total / span * 60 if total > 1 else 0.0

# busiest 10 s window, by sliding over each crossing
peak = 0
times = df["video_time_s"].tolist()
j = 0
for i, t in enumerate(times):
    while times[j] < t - 10:
        j += 1
    peak = max(peak, i - j + 1)

# ---------------------------------------------------------------- header
source = "bundled sample" if using_sample else "local database"
st.markdown(
    f"""
<div class="topbar">
  <div class="brand">SENTRA<small>VEHICLE FLOW ANALYTICS</small></div>
  <div class="meta">
    run <b>{run_id}</b> &nbsp;·&nbsp; source <b>{source}</b><br>
    window <b>{t0:.1f}–{t1:.1f} s</b> &nbsp;·&nbsp; pipeline <b>yolo11n / bytetrack / line crossing</b>
  </div>
</div>
<div class="kpis">
  <div class="kpi"><div class="kpi-l">Total crossings</div><div class="kpi-v">{total}</div>
    <div class="kpi-s">each track counted once</div></div>
  <div class="kpi"><div class="kpi-l">Inbound</div><div class="kpi-v">{inbound}</div>
    <div class="kpi-s">toward camera</div></div>
  <div class="kpi"><div class="kpi-l">Outbound</div><div class="kpi-v">{outbound}</div>
    <div class="kpi-s">away from camera</div></div>
  <div class="kpi"><div class="kpi-l">Flow rate</div><div class="kpi-v">{rate:.0f}</div>
    <div class="kpi-s">vehicles / min</div></div>
  <div class="kpi"><div class="kpi-l">Peak density</div><div class="kpi-v">{peak}</div>
    <div class="kpi-s">crossings in any 10 s</div></div>
</div>
""",
    unsafe_allow_html=True,
)

if total == 0:
    st.caption("This run has no crossings.")
    st.stop()

present = [t for t in TYPES if t in set(df["vehicle_type"])]

left, right = st.columns([2.1, 1], gap="large")

# ---------------------------------------------------------------- crossing log
with left:
    st.markdown('<div class="sec">Crossing log <span>one mark per vehicle · ▲ outbound</span></div>',
                unsafe_allow_html=True)
    fig = go.Figure()
    for vtype in present:
        for direction, symbol, size in (("toward", "line-ns-open", 18), ("away", "triangle-up-open", 10)):
            part = df[(df["vehicle_type"] == vtype) & (df["direction"] == direction)]
            if part.empty:
                continue
            fig.add_trace(go.Scatter(
                x=part["video_time_s"], y=[vtype] * len(part), mode="markers",
                marker=dict(symbol=symbol, size=size, color=TYPE_COLOR[vtype],
                            line=dict(width=2, color=TYPE_COLOR[vtype])),
                customdata=part[["track_id", "direction"]],
                hovertemplate="t %{x:.2f} s<br>id %{customdata[0]}<br>"
                              + vtype + " · %{customdata[1]}<extra></extra>",
            ))
    lay = base_layout(60 + 46 * len(present))
    lay["yaxis"].update(categoryorder="array", categoryarray=present[::-1], showgrid=False, color=INK_2)
    lay["xaxis"].update(title=dict(text="video time (s)", font=dict(size=10, color=INK_3)))
    fig.update_layout(**lay)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # ------------------------------------------------------------ throughput
    st.markdown(f'<div class="sec">Throughput <span>crossings per {bin_s} s bin</span></div>',
                unsafe_allow_html=True)
    start = (t0 // bin_s) * bin_s
    df["bin"] = start + ((df["video_time_s"] - start) // bin_s) * bin_s
    grid = (df.groupby(["bin", "vehicle_type"]).size().unstack(fill_value=0)
            .reindex(columns=present, fill_value=0))
    fig = go.Figure()
    for vtype in present:
        fig.add_trace(go.Bar(
            x=grid.index + bin_s / 2, y=grid[vtype], name=vtype, width=bin_s * 0.62,
            marker=dict(color=TYPE_COLOR[vtype], line=dict(color=BG, width=1.5)),
            hovertemplate=f"{vtype}<br>%{{x:.0f}} s ± {bin_s / 2:g}<br>%{{y}} crossings<extra></extra>",
        ))
    lay = base_layout(240)
    lay.update(barmode="stack", showlegend=True,
               legend=dict(orientation="h", y=1.12, x=0, traceorder="normal", font=dict(color=INK_2, size=11)))
    lay["yaxis"].update(title=dict(text="crossings", font=dict(size=10, color=INK_3)))
    fig.update_layout(**lay)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # ------------------------------------------------------------ cumulative
    st.markdown('<div class="sec">Cumulative count</div>', unsafe_allow_html=True)
    cum = df.reset_index(drop=True)
    fig = go.Figure(go.Scatter(
        x=cum["video_time_s"], y=cum.index + 1, mode="lines", line=dict(shape="hv", width=2, color=INK),
        hovertemplate="t %{x:.2f} s<br>%{y} total<extra></extra>",
    ))
    lay = base_layout(180)
    lay["yaxis"].update(rangemode="tozero")
    fig.update_layout(**lay)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

# ---------------------------------------------------------------- right column
with right:
    st.markdown('<div class="sec">Class mix</div>', unsafe_allow_html=True)
    mix = df["vehicle_type"].value_counts()
    rows = ""
    for vtype in present:
        n = int(mix.get(vtype, 0))
        rows += (f'<div class="row"><span><i style="display:inline-block;width:8px;height:8px;'
                 f'background:{TYPE_COLOR[vtype]};margin-right:8px"></i>{vtype}</span>'
                 f'<b>{n} <span style="color:{INK_3}">{n / total:.0%}</span></b></div>')
    st.markdown(rows, unsafe_allow_html=True)

    st.markdown('<div class="sec">Direction</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="row"><span>inbound</span><b>{inbound}</b></div>'
        f'<div class="bar"><i style="width:{inbound / total:.0%}"></i></div>'
        f'<div class="row"><span>outbound</span><b>{outbound}</b></div>'
        f'<div class="bar"><i style="width:{outbound / total:.0%}"></i></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sec">Measured accuracy <span>hand-counted</span></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="row"><span>clip</span><b>{EVAL["clip"]}</b></div>'
        f'<div class="row"><span>hand / system</span><b>{EVAL["hand"]} / {EVAL["system"]}</b></div>'
        f'<div class="row"><span>recall · direction</span><b>{EVAL["dir_recall"]:.2f}</b></div>'
        f'<div class="row"><span>precision · direction</span><b>{EVAL["dir_precision"]:.2f}</b></div>'
        f'<div class="row"><span>recall · direction + class</span><b>{EVAL["type_recall"]:.2f}</b></div>'
        f'<div class="row"><span>precision · direction + class</span><b>{EVAL["type_precision"]:.2f}</b></div>'
        '<div class="note">Main error: the same vehicle occasionally counted twice. '
        'Vans are often classed as truck (no van class in the training data).</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sec">Frame overlay</div>', unsafe_allow_html=True)
    gif = Path("docs/demo.gif")
    if gif.exists():
        st.image(str(gif))
    else:
        st.caption("Run `python count.py --gif docs/demo.gif` to create the preview.")

# ---------------------------------------------------------------- event table
st.markdown(f'<div class="sec">Event log <span>{total} rows</span></div>', unsafe_allow_html=True)
st.dataframe(
    df[["video_time_s", "track_id", "vehicle_type", "direction", "ts"]],
    width="stretch", hide_index=True, height=260,
    column_config={
        "video_time_s": st.column_config.NumberColumn("t (s)", format="%.2f"),
        "track_id": st.column_config.NumberColumn("track"),
        "vehicle_type": "class",
        "direction": "direction",
        "ts": st.column_config.DatetimeColumn("timestamp", format="HH:mm:ss.SSS"),
    },
)
