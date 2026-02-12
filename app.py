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
# SIDEBAR INPUTS
# =====================================================
st.sidebar.subheader("Span 7–21 Completed")
c_s1 = st.sidebar.number_input("Stringers Completed (7–21)", 0, TOTALS_SPAN1["Stringers"], 0)
c_cf1 = st.sidebar.number_input("Cross Frames Completed (7–21)", 0, TOTALS_SPAN1["Cross Frames"], 0)
c_cg1 = st.sidebar.number_input("Cross Girders Completed (7–21)", 0, TOTALS_SPAN1["Cross Girders"], 0)

st.sidebar.subheader("Span 22–36B Completed")
c_s2 = st.sidebar.number_input("Stringers Completed (22–36B)", 0, TOTALS_SPAN2["Stringers"], 0)
c_p2 = st.sidebar.number_input("Portals Completed", 0, TOTALS_SPAN2["Portals"], 0)

st.sidebar.subheader("Production Rates (per day for 2 crews)")
stringers_rate = st.sidebar.number_input("Stringers rate", 0.1, value=16.0)
cross_frames_rate = st.sidebar.number_input("Cross Frames rate", 0.1, value=10.0)
cross_girders_rate = st.sidebar.number_input("Cross Girders rate", 0.1, value=1.5)
portals_rate = st.sidebar.number_input("Portals rate", 0.1, value=2.0)

base_crews = st.sidebar.number_input("Base Crews", 1, value=2)
deadline_input = st.sidebar.date_input("Deadline", dt.date(today.year, 4, 30))

# =====================================================
# TEMP CREW ADJUSTMENT WINDOW
# =====================================================
st.sidebar.subheader("Temporary Crew Adjustment Window")

use_temp_window = st.sidebar.checkbox("Enable Temporary Crew Change")

if use_temp_window:
    temp_start = st.sidebar.date_input("Change Start Date", today)
    temp_end = st.sidebar.date_input("Change End Date", today + dt.timedelta(days=14))
    temp_crews = st.sidebar.number_input("Crews During Window", 1, value=3)
else:
    temp_start = None
    temp_end = None
    temp_crews = base_crews

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

# =====================================================
# REMAINING QUANTITIES
# =====================================================
r_s1 = max(TOTALS_SPAN1["Stringers"] - c_s1, 0)
r_cf1 = max(TOTALS_SPAN1["Cross Frames"] - c_cf1, 0)
r_cg1 = max(TOTALS_SPAN1["Cross Girders"] - c_cg1, 0)

r_s2 = max(TOTALS_SPAN2["Stringers"] - c_s2, 0)
r_p2 = max(TOTALS_SPAN2["Portals"] - c_p2, 0)

# Convert rates to per-crew
per_crew_rates_span1 = np.array([stringers_rate, cross_frames_rate, cross_girders_rate]) / 2
per_crew_rates_span2 = np.array([stringers_rate, portals_rate]) / 2

# =====================================================
# BUILD SCHEDULE
# =====================================================
def build_schedule(tasks, quantities, per_crew_rates, start_dt64):
    remaining = np.array(quantities, dtype=float)
    cumulative = [0.0]
    dates = [ensure_busday(start_dt64)]
    completion_dates = []

    current_day = ensure_busday(start_dt64)
    task_index = 0

    while task_index < len(tasks) and remaining.sum() > 0:
        current_day = ensure_busday(current_day)

        # Determine crews for this day
        if use_temp_window and temp_start <= to_pydate(current_day) <= temp_end:
            crews_today = temp_crews
        else:
            crews_today = base_crews

        daily_rate = per_crew_rates[task_index] * crews_today
        completed_today = min(daily_rate, remaining[task_index])

        remaining[task_index] -= completed_today
        cumulative.append(cumulative[-1] + completed_today)

        if remaining[task_index] <= 1e-9:
            completion_dates.append(current_day)
            task_index += 1

        current_day = np.busday_offset(current_day, 1)
        dates.append(current_day)

    return dates, cumulative, completion_dates

# =====================================================
# PLOT FUNCTION
# =====================================================
def plot_span(dates, curve, tasks, completion_dates, title):
    x = [to_pydate(d) for d in dates]
    fig, ax = plt.subplots(figsize=(15,6))
    ax.plot(x, curve, linewidth=3)

    colors = ["green", "orange", "purple", "blue"]

    for task, comp, color in zip(tasks, completion_dates, colors):
        comp_py = to_pydate(comp)
        ax.axvline(comp_py, linestyle="--", color=color)
        ax.text(
            comp_py,
            max(curve)*0.1,
            f"{task} Complete: {comp_py.strftime('%m/%d/%Y')}",
            rotation=90,
            fontsize=9,
            color=color,
            fontweight="bold"
        )

    ax.axvline(deadline_input, color="red", linewidth=3)
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
span1_dates, span1_curve, span1_completion = build_schedule(
    span1_tasks,
    [r_s1, r_cf1, r_cg1],
    per_crew_rates_span1,
    start_date
)

span1_finish = span1_completion[-1] if span1_completion else start_date

span2_tasks = ["Stringers", "Portals"]
span2_dates, span2_curve, span2_completion = build_schedule(
    span2_tasks,
    [r_s2, r_p2],
    per_crew_rates_span2,
    span1_finish
)

# =====================================================
# DISPLAY
# =====================================================
st.subheader("Span 7–21 Projection")
st.pyplot(plot_span(span1_dates, span1_curve, span1_tasks, span1_completion, "Span 7–21 Production"))

st.subheader("Span 22–36B Projection")
st.pyplot(plot_span(span2_dates, span2_curve, span2_tasks, span2_completion, "Span 22–36B Production"))
