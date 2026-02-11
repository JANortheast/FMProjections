import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt

st.set_page_config(page_title="FM Projections", layout="wide")
st.title("📊 FM Projections - Production Timeline")

# =====================================================
# AUTO START DATE (TODAY)
# =====================================================
today = dt.date.today()
start_date = np.datetime64(today)

# =====================================================
# SIDEBAR INPUTS
# =====================================================
st.sidebar.header("Project Parameters")

# -------------------------------
# Span 7–21 Quantities
# -------------------------------
st.sidebar.subheader("Span 7–21 Quantities (each)")

stringers = st.sidebar.number_input("Stringers (7–21)", 0, 10000, 852)
cross_frames = st.sidebar.number_input("Cross Frames (7–21)", 0, 10000, 82)
cross_girders = st.sidebar.number_input("Cross Girders (7–21)", 0, 10000, 22)

# -------------------------------
# Span 22–36B Quantities
# -------------------------------
st.sidebar.subheader("Span 22–36B Quantities (each)")

additional_stringers_span2 = st.sidebar.number_input(
    "Additional Stringers (22–36B)", 0, 10000, 1369
)

portals = st.sidebar.number_input("Portals (22–36B)", 0, 1000, 8)

# -------------------------------
# Production Rates (2 crews total)
# -------------------------------
st.sidebar.subheader("Production Rates (per day, 2 crews)")

stringers_rate_2 = st.sidebar.number_input("Stringers rate", 0.1, 100.0, 16.0)
cross_frames_rate_2 = st.sidebar.number_input("Cross Frames rate", 0.1, 100.0, 10.0)
cross_girders_rate_2 = st.sidebar.number_input("Cross Girders rate", 0.1, 100.0, 1.5)
portals_rate_2 = st.sidebar.number_input("Portals rate", 0.1, 100.0, 2.0)

rates_2 = np.array([
    stringers_rate_2,
    cross_frames_rate_2,
    cross_girders_rate_2,
    portals_rate_2
])

rate_per_crew = rates_2 / 2

# -------------------------------
# Base Crews
# -------------------------------
st.sidebar.subheader("Base Crews")
base_crews = st.sidebar.number_input("Base Number of Crews", 1, 20, 2)

# -------------------------------
# Deadline (Default = April 30 Current Year)
# -------------------------------
st.sidebar.subheader("Project Deadline")

default_deadline = dt.date(today.year, 4, 30)

deadline_input = st.sidebar.date_input(
    "Deadline Date",
    value=default_deadline
)

deadline_date = np.datetime64(deadline_input)

# =====================================================
# CREW WINDOWS
# =====================================================
st.sidebar.subheader("Temporary Crew Windows")

num_windows = st.sidebar.number_input("Number of Crew Windows", 0, 10, 0)

crew_windows = []
validation_errors = False

for i in range(int(num_windows)):
    st.sidebar.markdown(f"---")
    st.sidebar.markdown(f"**Window {i+1}**")

    crews = st.sidebar.number_input(
        f"Crews in Window {i+1}",
        1, 20, base_crews + 1,
        key=f"crews_{i}"
    )

    start = st.sidebar.date_input(
        f"Start {i+1}",
        value=today,
        key=f"start_{i}"
    )

    end = st.sidebar.date_input(
        f"End {i+1}",
        value=today + dt.timedelta(days=14),
        key=f"end_{i}"
    )

    if start >= end:
        st.sidebar.error(f"❌ Window {i+1} start must be before end.")
        validation_errors = True
    else:
        crew_windows.append({
            "index": i+1,
            "crews": crews,
            "start": np.datetime64(start),
            "end": np.datetime64(end)
        })

# Overlap check
crew_windows = sorted(crew_windows, key=lambda x: x["start"])
for i in range(len(crew_windows)-1):
    if crew_windows[i]["end"] > crew_windows[i+1]["start"]:
        st.sidebar.error("❌ Crew windows cannot overlap.")
        validation_errors = True

if validation_errors:
    st.stop()

# =====================================================
# CREW LOOKUP
# =====================================================
def get_crews(day):
    crews_today = base_crews
    for w in crew_windows:
        if w["start"] <= day < w["end"]:
            crews_today = w["crews"]
    return crews_today

# =====================================================
# SCHEDULER
# =====================================================
def build_schedule(quantities, rates, start):

    remaining = quantities.copy()
    cumulative = [0]
    dates = [start]

    current_day = start
    task_index = 0
    completion_dates = []

    while task_index < len(remaining):

        crews_today = get_crews(current_day)
        daily_rate = rates[task_index] * crews_today

        completed = min(daily_rate, remaining[task_index])
        remaining[task_index] -= completed

        cumulative.append(cumulative[-1] + completed)

        if remaining[task_index] <= 0:
            completion_dates.append(current_day)
            task_index += 1

        current_day = np.busday_offset(current_day, 1)
        dates.append(current_day)

    return dates, cumulative, completion_dates

# =====================================================
# SPAN 7–21
# =====================================================
span1_tasks = ["Stringers", "Cross Frames", "Cross Girders"]
span1_quantities = np.array([stringers, cross_frames, cross_girders])
span1_rates = rate_per_crew[:3]

span1_dates, span1_curve, span1_completion = build_schedule(
    span1_quantities,
    span1_rates,
    start_date
)

span1_finish = span1_completion[-1]

# =====================================================
# SPAN 22–36B
# =====================================================
span2_start = np.busday_offset(span1_finish, 1)

span2_tasks = ["Stringers", "Portals"]
span2_quantities = np.array([additional_stringers_span2, portals])
span2_rates = np.array([rate_per_crew[0], rate_per_crew[3]])

span2_dates, span2_curve, span2_completion = build_schedule(
    span2_quantities,
    span2_rates,
    span2_start
)

span2_finish = span2_completion[-1]

# =====================================================
# PLOT SPAN 7–21 (WITH DEADLINE + COMPLETION LABELS)
# =====================================================
fig1, ax1 = plt.subplots(figsize=(12,6))

ax1.plot(span1_dates, span1_curve, linewidth=3)

# Solid Red Deadline Line
ax1.axvline(deadline_date, color="red", linewidth=3)

# Label for deadline
ax1.text(
    deadline_date,
    max(span1_curve) * 0.9,
    "DEADLINE",
    rotation=90,
    color="red",
    fontweight="bold",
    verticalalignment="top"
)

# Dotted lines + vertical text for each task completion
for task, comp_date in zip(span1_tasks, span1_completion):
    ax1.axvline(comp_date, linestyle="--", alpha=0.7)

    ax1.text(
        comp_date,
        max(span1_curve) * 0.05,
        f"{task}\n{comp_date}",
        rotation=90,
        fontsize=9,
        fontweight="bold",
        verticalalignment="bottom"
    )

ax1.set_title("Span 7–21 Production Timeline")
ax1.set_ylabel("Items Completed (each)")
ax1.set_xlabel("Date")
ax1.grid(True)

st.pyplot(fig1)

# Deadline status
days_difference = int((deadline_date - span1_finish) / np.timedelta64(1, 'D'))

if days_difference >= 0:
    st.success(f"✅ Span 7–21 is {days_difference} days EARLY")
else:
    st.error(f"⚠️ Span 7–21 is {abs(days_difference)} days LATE")

# =====================================================
# PLOT SPAN 22–36B
# =====================================================
fig2, ax2 = plt.subplots(figsize=(12,6))

ax2.plot(span2_dates, span2_curve, linewidth=3)
ax2.set_title("Span 22–36B Production Timeline")
ax2.set_ylabel("Items Completed (each)")
ax2.set_xlabel("Date")
ax2.grid(True)

for task, comp_date in zip(span2_tasks, span2_completion):
    ax2.axvline(comp_date, linestyle="--", alpha=0.6)

st.pyplot(fig2)

# =====================================================
# SUMMARY
# =====================================================
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Completion Dates")
st.sidebar.write(f"Span 7–21 Finish: {span1_finish}")
st.sidebar.write(f"Span 22–36B Finish: {span2_finish}")
