import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt

st.set_page_config(page_title="FM Projections", layout="wide")
st.title("📊 FM Projections - Production Timeline")

# =====================================================
# TRUE TOTAL JOB QUANTITIES
# =====================================================
TOTALS_SPAN1 = {"Stringers": 1023, "Cross Frames": 130, "Cross Girders": 28}
TOTALS_SPAN2 = {"Stringers": 2429, "Portals": 16}

# =====================================================
# START DATE (BUSINESS DAY)
# =====================================================
today = dt.date.today()
start_date = np.datetime64(today, "D")
if not np.is_busday(start_date):
    start_date = np.busday_offset(start_date, 0, roll="forward")

# =====================================================
# SESSION STATE (multiple temp windows)
# =====================================================
if "temp_windows" not in st.session_state:
    st.session_state.temp_windows = []  # [{"start": date, "end": date, "crews": int}, ...]
if "temp_enabled" not in st.session_state:
    st.session_state.temp_enabled = False

# =====================================================
# SIDEBAR INPUTS
# =====================================================
st.sidebar.subheader("Span 7–21 Completed")
c_s1 = st.sidebar.number_input("Stringers Completed (7–21)", 0, TOTALS_SPAN1["Stringers"], 0, key="c_s1")
c_cf1 = st.sidebar.number_input("Cross Frames Completed (7–21)", 0, TOTALS_SPAN1["Cross Frames"], 0, key="c_cf1")
c_cg1 = st.sidebar.number_input("Cross Girders Completed (7–21)", 0, TOTALS_SPAN1["Cross Girders"], 0, key="c_cg1")

st.sidebar.subheader("Span 22–36B Completed")
c_s2 = st.sidebar.number_input("Stringers Completed (22–36B)", 0, TOTALS_SPAN2["Stringers"], 0, key="c_s2")
c_p2 = st.sidebar.number_input("Portals Completed", 0, TOTALS_SPAN2["Portals"], 0, key="c_p2")

st.sidebar.subheader("Production Rates (per day for 2 crews)")
stringers_rate = st.sidebar.number_input("Stringers rate", 0.1, value=16.0, key="stringers_rate")
cross_frames_rate = st.sidebar.number_input("Cross Frames rate", 0.1, value=10.0, key="cross_frames_rate")
cross_girders_rate = st.sidebar.number_input("Cross Girders rate", 0.1, value=1.5, key="cross_girders_rate")
portals_rate = st.sidebar.number_input("Portals rate", 0.1, value=2.0, key="portals_rate")

base_crews = st.sidebar.number_input("Base Crews", 1, value=2, key="base_crews")

deadline_input = st.sidebar.date_input(
    "Deadline (Span 7–21)",
    value=max(dt.date(today.year, 4, 30), today),
    min_value=today,
    key="deadline_input",
)

# =====================================================
# TEMP CREW ADJUSTMENT WINDOWS (multiple)
# =====================================================
st.sidebar.subheader("Temporary Crew Adjustment Windows")
st.session_state.temp_enabled = st.sidebar.checkbox(
    "Enable Temporary Crew Changes",
    value=st.session_state.temp_enabled,
    key="enable_temp",
)

if st.session_state.temp_enabled:
    new_start = st.sidebar.date_input(
        "New Window Start Date",
        value=today,
        min_value=today,
        key="new_window_start",
    )
    new_end = st.sidebar.date_input(
        "New Window End Date",
        value=new_start,
        min_value=new_start,
        key="new_window_end",
    )
    new_crews = st.sidebar.number_input(
        "Crews During New Window",
        min_value=1,
        value=3,
        key="new_window_crews",
    )

    col1, col2 = st.sidebar.columns(2)
    if col1.button("✅ Confirm / Add Window", key="add_window_btn"):
        st.session_state.temp_windows.append({"start": new_start, "end": new_end, "crews": int(new_crews)})
        st.rerun()

    if col2.button("🔄 Reset All Windows", key="reset_all_windows_btn"):
        st.session_state.temp_windows = []
        st.rerun()

    if st.session_state.temp_windows:
        st.sidebar.markdown("**Active windows (last wins if overlapping):**")
        for i, w in enumerate(st.session_state.temp_windows):
            cols = st.sidebar.columns([6, 2])
            cols[0].write(f"{i+1}) {w['start']} → {w['end']} | crews={w['crews']}")
            if cols[1].button("❌", key=f"del_window_{i}"):
                st.session_state.temp_windows.pop(i)
                st.rerun()

# =====================================================
# HELPERS
# =====================================================
def ensure_busday(d):
    d = np.datetime64(d, "D")
    if not np.is_busday(d):
        d = np.busday_offset(d, 0, roll="forward")
    return d

def to_pydate(d):
    return dt.date.fromisoformat(str(np.datetime64(d, "D")))

def overlap_window(x_min, x_max, w_start, w_end):
    a = max(x_min, w_start)
    b = min(x_max, w_end)
    if a <= b:
        return a, b
    return None

def crews_for_date(day: dt.date, base: int) -> int:
    # LAST window wins if overlapping
    if not st.session_state.temp_enabled:
        return base
    crews = base
    for w in st.session_state.temp_windows:
        if w["start"] <= day <= w["end"]:
            crews = int(w["crews"])
    return crews

# =====================================================
# REMAINING QUANTITIES (updates immediately)
# =====================================================
r_s1 = max(TOTALS_SPAN1["Stringers"] - c_s1, 0)
r_cf1 = max(TOTALS_SPAN1["Cross Frames"] - c_cf1, 0)
r_cg1 = max(TOTALS_SPAN1["Cross Girders"] - c_cg1, 0)

r_s2 = max(TOTALS_SPAN2["Stringers"] - c_s2, 0)
r_p2 = max(TOTALS_SPAN2["Portals"] - c_p2, 0)

# =====================================================
# DISPLAY TOTALS + COMPLETED + REMAINING (READ-ONLY + LIVE)
# =====================================================
st.subheader("Totals / Completed / Remaining")

colA, colB = st.columns(2)

with colA:
    st.markdown("### Span 7–21")
    st.markdown("**Totals**")
    t1, t2, t3 = st.columns(3)
    t1.metric("Stringers", TOTALS_SPAN1["Stringers"])
    t2.metric("Cross Frames", TOTALS_SPAN1["Cross Frames"])
    t3.metric("Cross Girders", TOTALS_SPAN1["Cross Girders"])

    st.markdown("**Completed**")
    c1, c2, c3 = st.columns(3)
    c1.metric("Stringers", c_s1)
    c2.metric("Cross Frames", c_cf1)
    c3.metric("Cross Girders", c_cg1)

    st.markdown("**Remaining**")
    r1, r2, r3 = st.columns(3)
    r1.metric("Stringers", int(r_s1))
    r2.metric("Cross Frames", int(r_cf1))
    r3.metric("Cross Girders", int(r_cg1))

with colB:
    st.markdown("### Span 22–36B")
    st.markdown("**Totals**")
    t1, t2 = st.columns(2)
    t1.metric("Stringers", TOTALS_SPAN2["Stringers"])
    t2.metric("Portals", TOTALS_SPAN2["Portals"])

    st.markdown("**Completed**")
    c1, c2 = st.columns(2)
    c1.metric("Stringers", c_s2)
    c2.metric("Portals", c_p2)

    st.markdown("**Remaining**")
    r1, r2 = st.columns(2)
    r1.metric("Stringers", int(r_s2))
    r2.metric("Portals", int(r_p2))

# Convert rates to per-crew (inputs are per day for 2 crews)
per_crew_rates_span1 = np.array([stringers_rate, cross_frames_rate, cross_girders_rate], dtype=float) / 2.0
per_crew_rates_span2 = np.array([stringers_rate, portals_rate], dtype=float) / 2.0

# =====================================================
# BUILD SCHEDULE (returns finish_date too)
# =====================================================
def build_schedule(tasks, quantities, per_crew_rates, start_dt64):
    remaining = np.array(quantities, dtype=float)
    cumulative = [0.0]
    dates = [ensure_busday(start_dt64)]
    completion_dates = []

    current_day = ensure_busday(start_dt64)
    task_index = 0
    finish_day = ensure_busday(start_dt64)

    while task_index < len(tasks) and remaining.sum() > 0:
        current_day = ensure_busday(current_day)
        day_py = to_pydate(current_day)

        crews_today = crews_for_date(day_py, base_crews)
        daily_rate = float(per_crew_rates[task_index]) * float(crews_today)
        completed_today = min(daily_rate, remaining[task_index])

        remaining[task_index] -= completed_today
        cumulative.append(cumulative[-1] + completed_today)

        if remaining[task_index] <= 1e-9:
            completion_dates.append(current_day)
            task_index += 1

        finish_day = current_day
        current_day = np.busday_offset(current_day, 1)
        dates.append(current_day)

    return dates, cumulative, completion_dates, finish_day

# =====================================================
# PLOT FUNCTION
# =====================================================
def plot_span(dates, curve, tasks, completion_dates, title, show_deadline=False, deadline_date=None, y_offset=0.0):
    x = [to_pydate(d) for d in dates]
    y = [v + y_offset for v in curve]

    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(x, y, linewidth=3)

    if st.session_state.temp_enabled and st.session_state.temp_windows:
        x_min, x_max = min(x), max(x)
        for w in st.session_state.temp_windows:
            ov = overlap_window(x_min, x_max, w["start"], w["end"])
            if ov:
                a, b = ov
                ax.axvspan(a, b, alpha=0.18)
                ax.text(
                    a,
                    (max(y) * 0.95) if max(y) > 0 else 0.0,
                    f"Temp crews: {w['crews']}",
                    fontsize=9,
                    fontweight="bold",
                    va="top",
                )

    colors = ["green", "orange", "purple", "blue"]
    label_y = (max(y) * 0.1) if max(y) > 0 else 0.0

    for task, comp, color in zip(tasks, completion_dates, colors):
        comp_py = to_pydate(comp)
        ax.axvline(comp_py, linestyle="--", color=color)
        ax.text(
            comp_py,
            label_y,
            f"{task} Complete: {comp_py.strftime('%m/%d/%Y')}",
            rotation=90,
            fontsize=9,
            color=color,
            fontweight="bold",
            va="bottom",
        )

    if show_deadline and deadline_date is not None:
        ax.axvline(deadline_date, color="red", linewidth=3)

    ax.set_title(title, fontweight="bold")
    ax.set_ylabel("Items Completed")
    ax.set_xlabel("Date")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig

# =====================================================
# RUN PROJECTIONS
# =====================================================
span1_tasks = ["Stringers", "Cross Frames", "Cross Girders"]
span1_dates, span1_curve, span1_completion, span1_finish_day = build_schedule(
    span1_tasks,
    [r_s1, r_cf1, r_cg1],
    per_crew_rates_span1,
    start_date,
)

span1_finish_date = to_pydate(span1_finish_day)
span1_end_value = span1_curve[-1] if len(span1_curve) else 0.0

span2_tasks = ["Stringers", "Portals"]
span2_dates, span2_curve, span2_completion, span2_finish_day = build_schedule(
    span2_tasks,
    [r_s2, r_p2],
    per_crew_rates_span2,
    span1_finish_day,
)

span2_finish_date = to_pydate(span2_finish_day)

# =====================================================
# DISPLAY (finish dates + graphs)
# =====================================================
st.subheader("Span 7–21 Projection")
st.write(f"**Projected finish (Span 7–21):** {span1_finish_date.strftime('%m/%d/%Y')}")
st.pyplot(
    plot_span(
        span1_dates,
        span1_curve,
        span1_tasks,
        span1_completion,
        "Span 7–21 Production",
        show_deadline=True,
        deadline_date=deadline_input,
        y_offset=0.0,
    )
)

st.subheader("Span 22–36B Projection")
st.write(f"**Projected finish (Span 22–36B):** {span2_finish_date.strftime('%m/%d/%Y')}")
st.pyplot(
    plot_span(
        span2_dates,
        span2_curve,
        span2_tasks,
        span2_completion,
        "Span 22–36B Production",
        show_deadline=False,
        deadline_date=None,
        y_offset=span1_end_value,
    )
)
