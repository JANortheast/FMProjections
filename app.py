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
st.sidebar.subheader("Span 7–21 Quantities (each)")

stringers = st.sidebar.number_input("Stringers (7–21)", min_value=0, value=852, step=1)
cross_frames = st.sidebar.number_input("Cross Frames (7–21)", min_value=0, value=82, step=1)
cross_girders = st.sidebar.number_input("Cross Girders (7–21)", min_value=0, value=22, step=1)

st.sidebar.subheader("Span 22–36B Quantities (each)")
additional_stringers_span2 = st.sidebar.number_input(
    "Additional Stringers (22–36B)",
    min_value=0,
    value=1369,
    step=1
)

portals = st.sidebar.number_input("Portals (22–36B)", min_value=0, value=8, step=1)

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
base_crews = st.sidebar.number_input("Base Number of Crews", min_value=1, value=2, step=1)

# =====================================================
# CREW WINDOWS WITH VALIDATION
# =====================================================
st.sidebar.subheader("Temporary Crew Windows")

num_windows = st.sidebar.number_input(
    "Number of Temporary Crew Windows",
    min_value=0,
    value=0,
    step=1
)

crew_windows = []
validation_errors = False

for i in range(int(num_windows)):
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Window {i+1}**")

    crews = st.sidebar.number_input(
        f"Crews During Window {i+1}",
        min_value=1,
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

    if start >= end:
        st.sidebar.error(f"❌ Window {i+1}: Start must be BEFORE End.")
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
    if crew_windows_sorted[i]["end"] > crew_windows_sorted[i+1]["start"]:
        st.sidebar.error(
            f"❌ Window {crew_windows_sorted[i]['index']} overlaps "
            f"with Window {crew_windows_sorted[i+1]['index']}."
        )
        validation_errors = True

if validation_errors:
    st.error("Fix crew window errors before generating schedule.")
    st.stop()

# =====================================================
# CREW LOOKUP FUNCTION
# =====================================================
def get_crews_for_day(day, base_crews, windows):
    crews_today = base_crews
    for w in windows:
        if w["start"] <= day < w["end"]:
            crews_today = w["crews"]
    return max(crews_today, 1)

# =====================================================
# GENERIC SCHEDULER
# =====================================================
def build_span_schedule(quantities, rates, start_date):

    remaining = quantities.copy()
    cumulative = [0]
    dates = [start_date]

    current_day = start_date
    task_index = 0
    task_completion_dates = []

    while task_index < len(remaining):

        crews_today = get_crews_for_day(current_day, base_crews, crew_windows)
        daily_rate = rates[task_index] * crews_today

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
# BUILD SPAN 7–21
# =====================================================
start_date = np.datetime64("2026-02-11")

span1_tasks = ["Stringers", "Cross Frames", "Cross Girders"]
span1_quantities = np.array([stringers, cross_frames, cross_girders], dtype=float)
span1_rates = rate_per_crew[:3]

span1_dates, span1_curve, span1_completion = build_span_schedule(
    span1_quantities,
    span1_rates,
    start_date
)

span1_finish = span1_completion[-1]

# =====================================================
# BUILD SPAN 22–36B (Starts After Span 1)
# =====================================================
span2_start = np.busday_offset(span1_finish, 1)

span2_tasks = ["Stringers", "Portals"]
span2_quantities = np.array([additional_stringers_span2, portals], dtype=float)
span2_rates = np.array([rate_per_crew[0], rate_per_crew[3]])

span2_dates, span2_curve, span2_completion = build_span_schedule(
    span2_quantities,
    span2_rates,
    span2_start
)

span2_finish = span2_completion[-1]

# =====================================================
# PLOT SPAN 7–21
# =====================================================
fig1, ax1 = plt.subplots(figsize=(12, 6))
ax1.plot(span1_dates, span1_curve, linewidth=3)
ax1.set_title("Span 7–21 Production Timeline", fontweight="bold")
ax1.set_ylabel("Items Completed (each)")
ax1.set_xlabel("Date")
ax1.grid(True)

for task, comp_date in zip(span1_tasks, span1_completion):
    ax1.axvline(comp_date, linestyle="--")
    ax1.text(comp_date, max(span1_curve)*0.05,
             f"{task}\n{comp_date}",
             rotation=90,
             fontsize=9)

st.pyplot(fig1)

# =====================================================
# PLOT SPAN 22–36B
# =====================================================
fig2, ax2 = plt.subplots(figsize=(12, 6))
ax2.plot(span2_dates, span2_curve, linewidth=3)
ax2.set_title("Span 22–36B Production Timeline", fontweight="bold")
ax2.set_ylabel("Items Completed (each)")
ax2.set_xlabel("Date")
ax2.grid(True)

for task, comp_date in zip(span2_tasks, span2_completion):
    ax2.axvline(comp_date, linestyle="--")
    ax2.text(comp_date, max(span2_curve)*0.05,
             f"{task}\n{comp_date}",
             rotation=90,
             fontsize=9)

st.pyplot(fig2)

# =====================================================
# SUMMARY
# =====================================================
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Span Completion Dates")
st.sidebar.write(f"Span 7–21 Finish: {span1_finish}")
st.sidebar.write(f"Span 22–36B Finish: {span2_finish}")
