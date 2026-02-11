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
# Task quantities
# -------------------------------
st.sidebar.subheader("Task Quantities")
stringers = st.sidebar.number_input("Stringers (units)", min_value=0, value=852, step=1)
cross_frames = st.sidebar.number_input("Cross Frames (units)", min_value=0, value=82, step=1)
cross_girders = st.sidebar.number_input("Cross Girders (units)", min_value=0, value=22, step=1)

tasks = ["Stringers", "Cross Frames", "Cross Girders"]
quantities = np.array([stringers, cross_frames, cross_girders], dtype=float)

# -------------------------------
# Production rates (TOTAL for 2 crews)
# -------------------------------
st.sidebar.subheader("Production Rates (per day, for 2 crews)")
stringers_rate_2crews = st.sidebar.number_input("Stringers rate", min_value=0.1, value=16.0, step=0.5)
cross_frames_rate_2crews = st.sidebar.number_input("Cross Frames rate", min_value=0.1, value=10.0, step=0.5)
cross_girders_rate_2crews = st.sidebar.number_input("Cross Girders rate", min_value=0.1, value=1.5, step=0.5)

rates_2_crews = np.array([stringers_rate_2crews, cross_frames_rate_2crews, cross_girders_rate_2crews])
rate_per_crew = rates_2_crews / 2

# -------------------------------
# Crew Configuration
# -------------------------------
st.sidebar.subheader("Crew Configuration")
num_crews = st.sidebar.number_input("Base Number of Crews", min_value=1, value=3, step=1)

# Temporary override
st.sidebar.subheader("Temporary Crew Increase")
use_override = st.sidebar.checkbox("Enable Temporary Crew Increase")

if use_override:
    override_crews = st.sidebar.number_input(
        "Crews During Override",
        min_value=1,
        value=num_crews + 1,
        step=1
    )

    override_start = st.sidebar.date_input(
        "Override Start Date",
        value=dt.date(2026, 4, 1)
    )

    override_end = st.sidebar.date_input(
        "Override End Date",
        value=dt.date(2026, 4, 15)
    )
else:
    override_crews = None
    override_start = None
    override_end = None

# -------------------------------
# Duration / Deadline
# -------------------------------
st.sidebar.subheader("Project Duration")
duration_workdays = st.sidebar.number_input("Duration (workdays)", min_value=1, value=57, step=1)

start_date = np.datetime64("2026-02-11")
deadline_date = np.busday_offset(start_date, duration_workdays)

total_units = int(sum(quantities))

# =====================================================
# VARIABLE CREW PRODUCTION FUNCTION
# =====================================================
def build_curve_variable_crews(
    quantities,
    rate_per_crew,
    base_crews,
    start_date,
    override_enabled=False,
    override_crews=None,
    override_start=None,
    override_end=None
):
    remaining = quantities.copy()
    cumulative = [0]
    dates = [start_date]

    current_day = start_date
    task_index = 0
    task_completion_dates = []

    while task_index < len(remaining):

        crews_today = base_crews

        if override_enabled:
            if np.datetime64(override_start) <= current_day <= np.datetime64(override_end):
                crews_today = override_crews

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
# BUILD CURVE
# =====================================================
dates, curve, task_completion_dates = build_curve_variable_crews(
    quantities=quantities,
    rate_per_crew=rate_per_crew,
    base_crews=num_crews,
    start_date=start_date,
    override_enabled=use_override,
    override_crews=override_crews,
    override_start=override_start,
    override_end=override_end
)

final_completion = task_completion_dates[-1]

# =====================================================
# PLOT
# =====================================================
fig, ax = plt.subplots(figsize=(14, 7))

ax.plot(dates, curve, linewidth=3, label=f"{num_crews} Base Crew(s)", marker="o", markersize=4)

# Deadline line
ax.axvline(deadline_date, color="red", linestyle="-", linewidth=3, label="Deadline")
ax.text(deadline_date, total_units * 0.95,
        "DEADLINE", color="red", rotation=90,
        va="top", ha="right", fontweight="bold")

# Milestones
colors = ["green", "orange", "purple"]

for task, comp_date, color in zip(tasks, task_completion_dates, colors):
    ax.axvline(comp_date, linestyle="--", linewidth=1.5, alpha=0.7, color=color)
    ax.text(comp_date, total_units * 0.05,
            f"{task}\n{comp_date}",
            rotation=90, va="bottom",
            fontsize=9, color=color, fontweight="bold")

# Override shading
if use_override:
    ax.axvspan(
        np.datetime64(override_start),
        np.datetime64(override_end),
        alpha=0.15
    )

ax.set_ylabel("Total Measurements Completed", fontweight="bold")
ax.set_xlabel("Date", fontweight="bold")
ax.set_ylim(0, max(total_units * 1.1, 100))
ax.set_title("Production Timeline with Variable Crews", fontweight="bold")
ax.grid(True, alpha=0.3)
ax.legend()

plt.tight_layout()
st.pyplot(fig)

# =====================================================
# SIDEBAR SUMMARY
# =====================================================
st.sidebar.markdown("---")
st.sidebar.subheader("📈 Summary")

col1, col2 = st.sidebar.columns(2)
with col1:
    st.metric("Total Units", total_units)
    st.metric("Start Date", str(start_date))
with col2:
    st.metric("Deadline", str(deadline_date))
    st.metric("Final Completion", str(final_completion))

st.sidebar.markdown("---")
st.sidebar.subheader("⏱️ Task Completion")

for task, comp_date in zip(tasks, task_completion_dates):
    st.sidebar.write(f"**{task}:** {comp_date}")

st.sidebar.markdown("---")

days_before_deadline = int((deadline_date - final_completion) / np.timedelta64(1, 'D'))

if days_before_deadline >= 0:
    st.sidebar.success(f"✅ ON SCHEDULE - Finishes {days_before_deadline} days early")
else:
    st.sidebar.error(f"⚠️ BEHIND SCHEDULE - Finishes {abs(days_before_deadline)} days late")
