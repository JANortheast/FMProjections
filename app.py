import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="FM Projections", layout="wide")
st.title("📊 FM Projections - Production Timeline")

# =====================================================
# TRUE TOTAL JOB QUANTITIES
# =====================================================
TOTALS_SPAN1 = {"Stringers": 1024, "Cross Frames": 130, "Cross Girders": 28}
TOTALS_SPAN2 = {"Stringers": 2115, "Portals": 16}

# =====================================================
# START DATE (BUSINESS DAY)
# =====================================================
today = dt.date.today()
start_date = np.datetime64(today, "D")
if not np.is_busday(start_date):
    start_date = np.busday_offset(start_date, 0, roll="forward")

# =====================================================
# SESSION STATE
# =====================================================
if "temp_windows" not in st.session_state:
    st.session_state.temp_windows = []

if "temp_enabled" not in st.session_state:
    st.session_state.temp_enabled = False

if "span1_selected" not in st.session_state:
    st.session_state.span1_selected = list(TOTALS_SPAN1.keys())

if "span2_selected" not in st.session_state:
    st.session_state.span2_selected = list(TOTALS_SPAN2.keys())

# =====================================================
# PAGE SELECTOR
# =====================================================
page = st.radio(
    "Select analysis type",
    ["Standard Projection (Manual Rates)", "Rate-Based Projection (Measured Rates)"],
    horizontal=True,
)

# =====================================================
# ENSURE RATE VARIABLES EXIST (FIXES NameError)
# =====================================================
stringers_rate = 0.0
cross_frames_rate = 0.0
cross_girders_rate = 0.0
portals_rate = 0.0

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
    if not st.session_state.temp_enabled:
        return base
    crews = base
    for w in st.session_state.temp_windows:
        if w["start"] <= day <= w["end"]:
            crews = int(w["crews"])
    return crews

def build_schedule(tasks, quantities, per_crew_rates, start_dt64, base_crews: int):
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

        if daily_rate <= 0:
            break

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

def plot_span(dates, curve, tasks, completion_dates, title,
              show_deadline=False, deadline_date=None, y_offset=0.0):

    x = [to_pydate(d) for d in dates]
    y = [v + y_offset for v in curve]

    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(x, y, linewidth=3)

    if show_deadline and deadline_date is not None:
        ax.axvline(deadline_date, color="red", linewidth=3)

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

    ax.set_title(title, fontweight="bold")
    ax.set_ylabel("Items Completed")
    ax.set_xlabel("Date")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig

# =====================================================
# SIDEBAR INPUTS
# =====================================================
st.sidebar.header("Inputs")

c_s1 = st.sidebar.number_input("Stringers Completed (7–21)", 0, TOTALS_SPAN1["Stringers"], 0)
c_cf1 = st.sidebar.number_input("Cross Frames Completed (7–21)", 0, TOTALS_SPAN1["Cross Frames"], 0)
c_cg1 = st.sidebar.number_input("Cross Girders Completed (7–21)", 0, TOTALS_SPAN1["Cross Girders"], 0)

c_s2 = st.sidebar.number_input("Stringers Completed (22–36B)", 0, TOTALS_SPAN2["Stringers"], 0)
c_p2 = st.sidebar.number_input("Portals Completed", 0, TOTALS_SPAN2["Portals"], 0)

base_crews = st.sidebar.number_input("Base Crews", 1, value=2)
deadline_input = st.sidebar.date_input("Deadline (Span 7–21)", value=today)

# =====================================================
# RATE INPUTS
# =====================================================
if page == "Standard Projection (Manual Rates)":
    stringers_rate = st.sidebar.number_input("Stringers rate", 0.1, value=16.0)
    cross_frames_rate = st.sidebar.number_input("Cross Frames rate", 0.1, value=10.0)
    cross_girders_rate = st.sidebar.number_input("Cross Girders rate", 0.1, value=1.5)
    portals_rate = st.sidebar.number_input("Portals rate", 0.1, value=2.0)
else:
    days_measured = st.sidebar.number_input("Days Measured", 0, value=0)
    if days_measured > 0:
        stringers_rate = c_s1 / days_measured
        cross_frames_rate = c_cf1 / days_measured
        cross_girders_rate = c_cg1 / days_measured
        portals_rate = c_p2 / days_measured

# =====================================================
# ITEM SELECTION
# =====================================================
st.sidebar.subheader("Display Items")

span1_selected = st.sidebar.multiselect(
    "Span 7–21 Items",
    list(TOTALS_SPAN1.keys()),
    default=st.session_state.span1_selected,
)
st.session_state.span1_selected = span1_selected

span2_selected = st.sidebar.multiselect(
    "Span 22–36B Items",
    list(TOTALS_SPAN2.keys()),
    default=st.session_state.span2_selected,
)
st.session_state.span2_selected = span2_selected

# =====================================================
# REMAINING
# =====================================================
r_s1 = max(TOTALS_SPAN1["Stringers"] - c_s1, 0)
r_cf1 = max(TOTALS_SPAN1["Cross Frames"] - c_cf1, 0)
r_cg1 = max(TOTALS_SPAN1["Cross Girders"] - c_cg1, 0)
r_s2 = max(TOTALS_SPAN2["Stringers"] - c_s2, 0)
r_p2 = max(TOTALS_SPAN2["Portals"] - c_p2, 0)

# =====================================================
# BUILD TASK LISTS BASED ON SELECTION
# =====================================================
span1_tasks, span1_qty, span1_rates = [], [], []

if "Stringers" in span1_selected:
    span1_tasks.append("Stringers")
    span1_qty.append(r_s1)
    span1_rates.append(stringers_rate / 2.0)

if "Cross Frames" in span1_selected:
    span1_tasks.append("Cross Frames")
    span1_qty.append(r_cf1)
    span1_rates.append(cross_frames_rate / 2.0)

if "Cross Girders" in span1_selected:
    span1_tasks.append("Cross Girders")
    span1_qty.append(r_cg1)
    span1_rates.append(cross_girders_rate / 2.0)

span2_tasks, span2_qty, span2_rates = [], [], []

if "Stringers" in span2_selected:
    span2_tasks.append("Stringers")
    span2_qty.append(r_s2)
    span2_rates.append(stringers_rate / 2.0)

if "Portals" in span2_selected:
    span2_tasks.append("Portals")
    span2_qty.append(r_p2)
    span2_rates.append(portals_rate / 2.0)

# =====================================================
# RUN PROJECTIONS
# =====================================================
if span1_tasks:
    span1_dates, span1_curve, span1_completion, span1_finish_day = build_schedule(
        span1_tasks, span1_qty, np.array(span1_rates), start_date, base_crews
    )
else:
    span1_dates, span1_curve, span1_completion = [], [0], []
    span1_finish_day = start_date

span1_finish_date = to_pydate(span1_finish_day)
span1_end_value = span1_curve[-1]

if span2_tasks:
    span2_dates, span2_curve, span2_completion, span2_finish_day = build_schedule(
        span2_tasks, span2_qty, np.array(span2_rates), span1_finish_day, base_crews
    )
else:
    span2_dates, span2_curve, span2_completion = [], [0], []
    span2_finish_day = span1_finish_day

span2_finish_date = to_pydate(span2_finish_day)

# =====================================================
# DISPLAY
# =====================================================
st.subheader("Span 7–21 Projection")
st.write(f"Projected finish: {span1_finish_date.strftime('%m/%d/%Y')}")
if span1_tasks:
    st.pyplot(plot_span(span1_dates, span1_curve, span1_tasks,
                        span1_completion,
                        "Span 7–21 Production",
                        True,
                        deadline_input,
                        0.0))

st.subheader("Span 22–36B Projection")
st.write(f"Projected finish: {span2_finish_date.strftime('%m/%d/%Y')}")
if span2_tasks:
    st.pyplot(plot_span(span2_dates, span2_curve, span2_tasks,
                        span2_completion,
                        "Span 22–36B Production",
                        False,
                        None,
                        span1_end_value))
