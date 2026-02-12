import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt

st.set_page_config(page_title="FM Projections", layout="wide")
st.title("📊 FM Projections - Production Timeline (Standard Projection)")

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
# SIDEBAR INPUTS (Standard Projection Only)
# =====================================================
st.sidebar.subheader("Span 7–21 Completed")
c_s1 = st.sidebar.number_input("Stringers Completed (7–21)", 0, TOTALS_SPAN1["Stringers"], 0, key="c_s1")
c_cf1 = st.sidebar.number_input("Cross Frames Completed (7–21)", 0, TOTALS_SPAN1["Cross Frames"], 0, key="c_cf1")
c_cg1 = st.sidebar.number_input("Cross Girders Completed (7–21)", 0, TOTALS_SPAN1["Cross Girders"], 0, key="c_cg1")

st.sidebar.subheader("Span 22–36B Completed")
c_s2 = st.sidebar.number_input("Stringers Completed (22–36B)", 0, TOTALS_SPAN2["Stringers"], 0, key="c_s2")
c_p2 = st.sidebar.number_input("Portals Completed", 0, TOTALS_SPAN2["Portals"], 0, key="c_p2")

st.sidebar.subheader("Days Already Worked by 2 Crews")
days_worked_s1 = st.sidebar.number_input("Span 7–21 Days", 0, 365, 0, key="days_worked_s1")
days_worked_s2 = st.sidebar.number_input("Span 22–36B Days", 0, 365, 0, key="days_worked_s2")

st.sidebar.subheader("Production Rates (per day for 2 crews)")
stringers_rate = st.sidebar.number_input("Stringers rate", min_value=0.1, value=16.0, step=0.1, key="stringers_rate")
cross_frames_rate = st.sidebar.number_input("Cross Frames rate", min_value=0.1, value=10.0, step=0.1, key="cross_frames_rate")
cross_girders_rate = st.sidebar.number_input("Cross Girders rate", min_value=0.1, value=1.5, step=0.1, key="cross_girders_rate")
portals_rate = st.sidebar.number_input("Portals rate", min_value=0.1, value=2.0, step=0.1, key="portals_rate")

base_crews = st.sidebar.number_input("Base Crews", min_value=1, value=2, step=1, key="base_crews")
deadline_input = st.sidebar.date_input("Deadline", dt.date(today.year, 4, 30), key="deadline_tab1")

# =====================================================
# HELPERS
# =====================================================
def ensure_busday(d: np.datetime64) -> np.datetime64:
    d = np.datetime64(d, "D")
    if not np.is_busday(d):
        d = np.busday_offset(d, 0, roll="forward")
    return d

def to_pydate(d: np.datetime64) -> dt.date:
    return dt.date.fromisoformat(str(np.datetime64(d, "D")))

# =====================================================
# STANDARD PROJECTION LOGIC
# =====================================================
st.subheader("Standard Projection")

# UI rates are "per day for 2 crews". Convert to per-crew, then multiply by base_crews in schedule.
per_crew_rates_span1 = np.array([stringers_rate, cross_frames_rate, cross_girders_rate], dtype=float) / 2.0
per_crew_rates_span2 = np.array([stringers_rate, portals_rate], dtype=float) / 2.0

# Remaining quantities (kept consistent with your prior logic)
r_s1 = max(TOTALS_SPAN1["Stringers"] - c_s1 - (stringers_rate * days_worked_s1 / 2), 0)
r_cf1 = max(TOTALS_SPAN1["Cross Frames"] - c_cf1 - (cross_frames_rate * days_worked_s1 / 2), 0)
r_cg1 = max(TOTALS_SPAN1["Cross Girders"] - c_cg1 - (cross_girders_rate * days_worked_s1 / 2), 0)

r_s2 = max(TOTALS_SPAN2["Stringers"] - c_s2 - (stringers_rate * days_worked_s2 / 2), 0)
r_p2 = max(TOTALS_SPAN2["Portals"] - c_p2 - (portals_rate * days_worked_s2 / 2), 0)

def build_schedule(tasks, quantities, per_crew_rates, start_dt64):
    remaining = np.array(quantities, dtype=float).copy()
    cumulative = [0.0]
    dates = [ensure_busday(start_dt64)]
    completion_dates = []

    current_day = ensure_busday(start_dt64)
    task_index = 0

    while task_index < len(tasks) and remaining.sum() > 0:
        current_day = ensure_busday(current_day)

        daily_rate = float(per_crew_rates[task_index]) * float(base_crews)
        completed_today = min(daily_rate, remaining[task_index])

        remaining[task_index] -= completed_today
        cumulative.append(cumulative[-1] + completed_today)

        if remaining[task_index] <= 1e-9:
            completion_dates.append(current_day)
            task_index += 1

        current_day = np.busday_offset(current_day, 1)
        dates.append(current_day)

    return dates, cumulative, completion_dates

def plot_span(dates, curve, tasks, completion_dates, title, show_deadline, deadline_date):
    x = [to_pydate(d) for d in dates]
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(x, curve, linewidth=3)

    colors = ["green", "orange", "purple", "blue"]
    y_text = (max(curve) * 0.1) if max(curve) > 0 else 0.0

    for task, comp, color in zip(tasks, completion_dates, colors):
        comp_py = to_pydate(comp)
        ax.axvline(comp_py, linestyle="--", color=color)
        ax.text(
            comp_py,
            y_text,
            f"{task} Done\n{comp_py.isoformat()}",
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

# Span 7–21
span1_tasks = ["Stringers", "Cross Frames", "Cross Girders"]
span1_quantities = [r_s1, r_cf1, r_cg1]
span1_dates, span1_curve, span1_completion = build_schedule(
    span1_tasks, span1_quantities, per_crew_rates_span1, start_date
)
span1_finish = span1_completion[-1] if span1_completion else ensure_busday(start_date)

# Span 22–36B (starts after span 7–21 finishes)
span2_tasks = ["Stringers", "Portals"]
span2_quantities = [r_s2, r_p2]
span2_dates, span2_curve, span2_completion = build_schedule(
    span2_tasks, span2_quantities, per_crew_rates_span2, span1_finish
)

st.subheader("Span 7–21 Remaining Projection")
st.pyplot(plot_span(span1_dates, span1_curve, span1_tasks, span1_completion, "Span 7–21 Production", True, deadline_input))

st.subheader("Span 22–36B Remaining Projection")
st.pyplot(plot_span(span2_dates, span2_curve, span2_tasks, span2_completion, "Span 22–36B Production", False, None))
