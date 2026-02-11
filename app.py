import streamlit as st
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="FM Projections", layout="wide")
st.title("📊 FM Projections - Production Timeline")

# =====================================================
# SIDEBAR INPUTS
# =====================================================
st.sidebar.header("Project Parameters")

# Task quantities (dynamic inputs)
st.sidebar.subheader("Task Quantities")
stringers = st.sidebar.number_input("Stringers (units)", min_value=0, value=852, step=1)
cross_frames = st.sidebar.number_input("Cross Frames (units)", min_value=0, value=82, step=1)
cross_girders = st.sidebar.number_input("Cross Girders (units)", min_value=0, value=22, step=1)

tasks = ["Stringers", "Cross Frames", "Cross Girders"]
quantities = [stringers, cross_frames, cross_girders]

# Production rates (TOTAL for 2 crews)
st.sidebar.subheader("Production Rates (per day, for 2 crews)")
stringers_rate_2crews = st.sidebar.number_input("Stringers rate", min_value=0.1, value=16.0, step=0.5)
cross_frames_rate_2crews = st.sidebar.number_input("Cross Frames rate", min_value=0.1, value=10.0, step=0.5)
cross_girders_rate_2crews = st.sidebar.number_input("Cross Girders rate", min_value=0.1, value=1.5, step=0.5)

rates_2_crews = np.array([stringers_rate_2crews, cross_frames_rate_2crews, cross_girders_rate_2crews])
rate_per_crew = rates_2_crews / 2

# Dynamic crew input
st.sidebar.subheader("Crew Configuration")
num_crews = st.sidebar.number_input("Number of Crews", min_value=1, value=3, step=1)

# Duration input
st.sidebar.subheader("Project Duration")
duration_workdays = st.sidebar.number_input("Duration (workdays)", min_value=1, value=57, step=1)

# Start date
start_date = np.datetime64("2026-02-11")
deadline_date = np.busday_offset(start_date, duration_workdays)

total_units = sum(quantities)

# =====================================================
# FUNCTION TO BUILD PRODUCTION CURVE (WORKDAYS ONLY)
# =====================================================
def build_curve_workdays(quantities, rates, start_date):
    cumulative = [0]
    dates = [start_date]
    current_day = start_date

    for qty, rate in zip(quantities, rates):
        remaining = qty
        days_needed = int(np.ceil(qty / rate))

        for _ in range(days_needed):
            completed = min(rate, remaining)
            remaining -= completed
            cumulative.append(cumulative[-1] + completed)
            current_day = np.busday_offset(current_day, 1)
            dates.append(current_day)

    return dates, cumulative

# =====================================================
# PLOTTING - SINGLE GRAPH
# =====================================================
fig, ax = plt.subplots(figsize=(14, 7))

rates = rate_per_crew * num_crews
dates, curve = build_curve_workdays(quantities, rates, start_date)

# Task durations (workdays)
durations = [int(np.ceil(q / r)) for q, r in zip(quantities, rates)]
milestones = np.cumsum(durations)

stringers_done = np.busday_offset(start_date, milestones[0])
cf_done = np.busday_offset(start_date, milestones[1])
cg_done = np.busday_offset(start_date, milestones[2])

# Production curve
ax.plot(dates, curve, linewidth=3, label=f"{num_crews} Crew(s)", color="steelblue", marker="o", markersize=4)

# SOLID RED DEADLINE
ax.axvline(deadline_date, color="red", linestyle="-", linewidth=3, label="Deadline")
ax.text(deadline_date, total_units * 0.95,
        "DEADLINE", color="red", rotation=90,
        va="top", ha="right", fontweight="bold", fontsize=11)

# Milestone lines
ax.axvline(stringers_done, linestyle="--", linewidth=1.5, alpha=0.7, color="green")
ax.axvline(cf_done, linestyle="--", linewidth=1.5, alpha=0.7, color="orange")
ax.axvline(cg_done, linestyle="--", linewidth=1.5, alpha=0.7, color="purple")

ax.text(stringers_done, total_units * 0.05,
        f"Stringers\n{stringers_done}", rotation=90, va="bottom", fontsize=9, color="green", fontweight="bold")
ax.text(cf_done, total_units * 0.05,
        f"Cross Frames\n{cf_done}", rotation=90, va="bottom", fontsize=9, color="orange", fontweight="bold")
ax.text(cg_done, total_units * 0.05,
        f"Cross Girders\n{cg_done}", rotation=90, va="bottom", fontsize=9, color="purple", fontweight="bold")

# Formatting
ax.set_ylabel("Total Measurements Completed", fontsize=12, fontweight="bold")
ax.set_xlabel("Date", fontsize=12, fontweight="bold")
ax.set_ylim(0, max(total_units * 1.1, 100))
ax.set_title(f"Production Timeline - {num_crews} Crew(s)", fontsize=14, fontweight="bold")
ax.grid(True, alpha=0.3)
ax.legend(loc="upper left", fontsize=11)

plt.tight_layout()
st.pyplot(fig)

# =====================================================
# METRICS AND SUMMARY
# =====================================================
st.sidebar.markdown("---")
st.sidebar.subheader("📈 Summary")

col1, col2 = st.sidebar.columns(2)
with col1:
    st.metric("Total Units", f"{total_units}")
    st.metric("Start Date", str(start_date))
with col2:
    st.metric("Duration", f"{duration_workdays} days")
    st.metric("Deadline", str(deadline_date))

st.sidebar.markdown("---")
st.sidebar.subheader("⏱️ Task Completion Times")
for task, duration, completion_date in zip(tasks, durations, [stringers_done, cf_done, cg_done]):
    st.sidebar.write(f"**{task}:** {duration} workdays → {completion_date}")

# =====================================================
# DEADLINE STATUS
# =====================================================
st.sidebar.markdown("---")
final_completion = cg_done
days_before_deadline = int((deadline_date - final_completion) / np.timedelta64(1, 'D'))

if days_before_deadline >= 0:
    st.sidebar.success(f"✅ **ON SCHEDULE** - Finishes {days_before_deadline} days before deadline")
else:
    st.sidebar.error(f"⚠️ **BEHIND SCHEDULE** - Finishes {abs(days_before_deadline)} days after deadline")