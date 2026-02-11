import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt

st.set_page_config(page_title="FM Projections", layout="wide")
st.title("📊 FM Projections - Production Timeline")

# =====================================================
# SIDEBAR INPUTS
# =====================================================
st.sidebar.header("Project Parameters")

# -------------------------------
# Task quantities (ALL IN EACH)
# -------------------------------
st.sidebar.subheader("Task Quantities (each)")

stringers = st.sidebar.number_input("Stringers (each)", min_value=0, value=852, step=1)
cross_frames = st.sidebar.number_input("Cross Frames (each)", min_value=0, value=82, step=1)
cross_girders = st.sidebar.number_input("Cross Girders (each)", min_value=0, value=22, step=1)
portals = st.sidebar.number_input("Portals (each)", min_value=0, value=8, step=1)

tasks = ["Stringers", "Cross Frames", "Cross Girders", "Portals"]
quantities = np.array([stringers, cross_frames, cross_girders, portals], dtype=float)

# -------------------------------
# Production rates (TOTAL for 2 crews)
# -------------------------------
st.sidebar.subheader("Production Rates (per day, for 2 crews)")

stringers_rate_2crews = st.sidebar.number_input("Stringers rate", min_value=0.1, value=16.0, step=0.5)
cross_frames_rate_2crews = st.sidebar.number_input("Cross Frames rate", min_value=0.1, value=10.0, step=0.5)
cross_girders_rate_2crews = st.sidebar.number_input("Cross Girders rate", min_value=0.1, value=1.5, step=0.5)
portals_rate_2crews = st.sidebar.number_input("Portals rate", min_value=0.1, value=2.0, step=0.5)

rates_2_crews = np.array([
    stringers_rate_2crews,
    cross_frames_rate_2crews,
    cross_girders_rate_2crews,
    portals_rate_2crews
])

rate_per_crew = rates_2_crews / 2

# -------------------------------
# Base crews
# -------------------------------
st.sidebar.subheader("Base Crew Configuration")
base_crews = st.sidebar.number_input("Base Number of Crews", min_value=1, value=0, step=1)

# =====================================================
# MULTIPLE CREW WINDOWS WITH VALIDATION
# =====================================================
st.sidebar.subheader("Temporary Crew Windows")

num_windows = st.sidebar.number_input(
    "Number of Temporary Crew Windows",
    min_value=0,
    value=1,
    step=1
)

crew_windows = []
validation_errors = False

for i in range(int(num_windows)):
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Window {i+1}**")

    crews = st.sidebar.number_input(
        f"Crews During Window {i+1}",
        min_value=0,
        value=base_crews + 1,
        step=1,
        key=f"crews_{i}"
    )

    start = st.sidebar.date_input(
        f"Start Date {i+1}",
        value=dt.date(2026, 4, 1),
        key=f"start_{i}"
    )

    end = st.sidebar.date_input(
        f"End Date {i+1}",
        value=dt.date(2026, 4, 15),
        key=f"end_{i}"
    )

    if start > end:
        st.sidebar.error(f"❌ Window {i+1}: Start date cannot be after End date.")
        validation_errors = True
    else:
        crew_windows.append({
            "index": i + 1,
            "crews": crews,
            "start": np.datetime64(start),
            "end": np.datetime64(end)
        })

# Overlap validation
crew_windows_sorted = sorted(crew_windows, key=lambda x: x["start"])

for i in range(len(crew_windows_sorted) - 1):
    current = crew_windows_sorted[i]
    next_window = crew_windows_sorted[i + 1]

    if current["end"] >= next_window["start"]:
        st.sidebar.error(
            f"❌ Window {current['index']} overlaps with Window {next_window['index']}."
        )
        validation_errors = True

# -------------------------------
# Duration / Deadline
# -------------------------------
st.sidebar.subheader("Project Duration")
duration_workdays = st.sidebar.number_input("Duration (workdays)", min_value=1, value=57, step=1)

start_date = np.datetime64("2026-02-11")
deadline_date = np.busday_offset(start_date, duration_workdays)

total_units = int(sum(quantities))

if validation_errors:
    st.error("Fix crew window errors before generating schedule.")
    st.stop()

# =====================================================
# CREW LOOKUP FUNCTION
# =====================================================
def get_crews_for_day(day, base_crews, windows):
    crews_today = base_crews
    for w in windows:
        if w["start"] <= day <= w["end"]:
            crews_today = w["crews"]
    return crews_today

# =====================================================
# BUILD SCHEDULE
# =====================================================
def build_curve_variable_crews(quantities, rate_per_crew, base_crews, windows, start_date):

    remaining = quantities.copy()
    cumulative = [0]
    dates = [start_date]

    current_day = start_date
    task_index = 0
    task_completion_dates = []

    while task_index < len(remaining):

        crews_today = get_crews_for_day(current_day, base_crews, windows)
        daily_rate = rate_per_crew[task_index] * crews_today

        completed = min(daily_rate, remaining[task_index])
        remaining[task_index] -= completed

        cumulative.append(cumulative[-1] + completed)

        if remaining[task_index] <= 0:
            task_completion_dates.append(current_day)
            task_index += 1

        current_day = np.busday_offset(current_day, 1)
        dates.append(current_day)

    return dates, cumulative, task_completion_dates

# =====================================================
# GENERATE CURVE
# =====================================================
dates, curve, task_completion_dates = build_curve_variable_crews(
    quantities,
    rate_per_crew,
    base_crews,
    crew_windows,
    start_date
)

final_completion = task_completion_dates[-1]

# =====================================================
# PLOT
# =====================================================
fig, ax = plt.subplots(figsize=(14, 7))

ax.plot(dates, curve, linewidth=3, marker="o", markersize=4, label="Production Curve")
ax.axvline(deadline_date, color="red", linewidth=3, label="Deadline")

colors = ["green", "orange", "purple", "blue"]

for task, comp_date, color in zip(tasks, task_completion_dates, colors):
    ax.axvline(comp_date, linestyle="--", alpha=0.7, color=color)
    ax.text(comp_date, total_units * 0.05,
            f"{task}\n{comp_date}",
            rotation=90,
            fontsize=9,
            color=color,
            fontweight="bold")

for w in crew_windows:
    ax.axvspan(w["start"], w["end"], alpha=0.15)

ax.set_ylabel("Total Items Completed (each)", fontweight="bold")
ax.set_xlabel("Date", fontweight="bold")
ax.set_ylim(0, max(total_units * 1.1, 100))
ax.set_title("Production Timeline with Validated Crew Windows", fontweight="bold")
ax.grid(True, alpha=0.3)
ax.legend()

plt.tight_layout()
st.pyplot(fig)

# =====================================================
# SUMMARY
# =====================================================
st.sidebar.markdown("---")
st.sidebar.subheader("📈 Summary")

col1, col2 = st.sidebar.columns(2)

with col1:
    st.metric("Total Items (each)", total_units)
    st.metric("Start Date", str(start_date))

with col2:
    st.metric("Deadline", str(deadline_date))
    st.metric("Final Completion", str(final_completion))

st.sidebar.markdown("---")

days_before_deadline = int((deadline_date - final_completion) / np.timedelta64(1, 'D'))

if days_before_deadline >= 0:
    st.sidebar.success(f"✅ ON SCHEDULE - {days_before_deadline} days early")
else:
    st.sidebar.error(f"⚠️ BEHIND SCHEDULE - {abs(days_before_deadline)} days late")
