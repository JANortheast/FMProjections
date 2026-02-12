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
start_date = np.datetime64(today)
if not np.is_busday(start_date):
    start_date = np.busday_offset(start_date, 0, roll="forward")

# =====================================================
# COMPLETED INPUTS
# =====================================================
st.sidebar.subheader("Span 7–21 Completed")
c_s1 = st.sidebar.number_input("Stringers Completed (7–21)", 0, TOTALS_SPAN1["Stringers"], 0)
c_cf1 = st.sidebar.number_input("Cross Frames Completed (7–21)", 0, TOTALS_SPAN1["Cross Frames"], 0)
c_cg1 = st.sidebar.number_input("Cross Girders Completed (7–21)", 0, TOTALS_SPAN1["Cross Girders"], 0)

st.sidebar.subheader("Span 22–36B Completed")
c_s2 = st.sidebar.number_input("Stringers Completed (22–36B)", 0, TOTALS_SPAN2["Stringers"], 0)
c_p2 = st.sidebar.number_input("Portals Completed", 0, TOTALS_SPAN2["Portals"], 0)

# =====================================================
# DAYS ALREADY WORKED BY 2 CREWS
# =====================================================
st.sidebar.subheader("Days Already Worked by 2 Crews")
days_worked_s1 = st.sidebar.number_input("Span 7–21 Days", 0, 365, 0)
days_worked_s2 = st.sidebar.number_input("Span 22–36B Days", 0, 365, 0)

# =====================================================
# RATES
# =====================================================
st.sidebar.subheader("Production Rates (per day for 2 crews)")
stringers_rate = st.sidebar.number_input("Stringers rate", 0.1, value=16.0)
cross_frames_rate = st.sidebar.number_input("Cross Frames rate", 0.1, value=10.0)
cross_girders_rate = st.sidebar.number_input("Cross Girders rate", 0.1, value=1.5)
portals_rate = st.sidebar.number_input("Portals rate", 0.1, value=2.0)

rates_2_crews = np.array([stringers_rate, cross_frames_rate, cross_girders_rate, portals_rate])
rate_per_crew = rates_2_crews / 2

# =====================================================
# BASE CREWS
# =====================================================
base_crews = st.sidebar.number_input("Base Crews", 1, value=2)

# =====================================================
# DEADLINE
# =====================================================
deadline_input = st.sidebar.date_input("Deadline", dt.date(today.year, 4, 30))
deadline_date = np.datetime64(deadline_input)

# =====================================================
# TEMP WINDOWS (CONFIRM-ONLY STORAGE)
# =====================================================
st.sidebar.subheader("Temporary Crew Windows")
if "confirmed_windows" not in st.session_state:
    st.session_state.confirmed_windows = {}

num_windows = st.sidebar.number_input("Number of Windows", 0, 5, 0)
for i in range(int(num_windows)):
    st.sidebar.markdown("---")
    crews = st.sidebar.number_input(
        f"Crews During Window {i+1}", 1, value=base_crews+1, key=f"crews_{i}"
    )
    start = st.sidebar.date_input(f"Start Date {i+1}", today, key=f"start_{i}")
    end = st.sidebar.date_input(f"End Date {i+1}", today + dt.timedelta(days=14), key=f"end_{i}")

    if st.sidebar.button(f"Confirm Window {i+1}", key=f"confirm_{i}"):
        st.session_state.confirmed_windows[i] = {
            "crews": crews,
            "start": np.datetime64(start),
            "end": np.datetime64(end)
        }
        st.sidebar.success("✅ Window Confirmed")

crew_windows = list(st.session_state.confirmed_windows.values())

# =====================================================
# CALCULATE REMAINING QUANTITIES
# =====================================================
# Base remaining
r_s1 = TOTALS_SPAN1["Stringers"] - c_s1
r_cf1 = TOTALS_SPAN1["Cross Frames"] - c_cf1
r_cg1 = TOTALS_SPAN1["Cross Girders"] - c_cg1
r_s2 = TOTALS_SPAN2["Stringers"] - c_s2
r_p2 = TOTALS_SPAN2["Portals"] - c_p2

# Subtract production already done by days worked (2 crews)
r_s1 -= stringers_rate * days_worked_s1 / 2
r_cf1 -= cross_frames_rate * days_worked_s1 / 2
r_cg1 -= cross_girders_rate * days_worked_s1 / 2
r_s2 -= stringers_rate * days_worked_s2 / 2
r_p2 -= portals_rate * days_worked_s2 / 2

# Prevent negative
r_s1 = max(r_s1,0)
r_cf1 = max(r_cf1,0)
r_cg1 = max(r_cg1,0)
r_s2 = max(r_s2,0)
r_p2 = max(r_p2,0)

# =====================================================
# CREW LOOKUP
# =====================================================
def get_crews_for_day(day):
    crews_today = base_crews
    for w in crew_windows:
        if w["start"] <= day <= w["end"]:
            crews_today = w["crews"]
    return crews_today

# =====================================================
# SCHEDULER
# =====================================================
def build_schedule(tasks, quantities, rates, start_date):
    remaining = quantities.copy()
    cumulative = [0]
    dates = [start_date]
    completion_dates = []
    current_day = start_date
    task_index = 0

    while task_index < len(tasks) and sum(remaining) > 0:
        if not np.is_busday(current_day):
            current_day = np.busday_offset(current_day, 0, roll="forward")

        crews_today = get_crews_for_day(current_day)
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
# BUILD SPAN 7–21
# =====================================================
span1_tasks = ["Stringers", "Cross Frames", "Cross Girders"]
span1_quantities = np.array([r_s1, r_cf1, r_cg1])
span1_dates, span1_curve, span1_completion = build_schedule(span1_tasks, span1_quantities, rate_per_crew[:3], start_date)
span1_finish = span1_completion[-1] if span1_completion else start_date

# =====================================================
# BUILD SPAN 22–36B
# =====================================================
span2_tasks = ["Stringers", "Portals"]
span2_quantities = np.array([r_s2, r_p2])
span2_dates, span2_curve, span2_completion = build_schedule(
    span2_tasks, span2_quantities, np.array([rate_per_crew[0], rate_per_crew[3]]), span1_finish
)
span2_finish = span2_completion[-1] if span2_completion else span1_finish

# =====================================================
# WINDOW SPLITTING PER SPAN
# =====================================================
def get_windows_for_span(span_start, span_end):
    span_windows = []
    for w in crew_windows:
        if w["end"] < span_start or w["start"] > span_end:
            continue
        start = max(w["start"], span_start)
        end = min(w["end"], span_end)
        span_windows.append({"start": start, "end": end})
    return span_windows

# =====================================================
# PLOTTING FUNCTION
# =====================================================
def plot_span(dates, curve, tasks, completion_dates, title, show_deadline):
    fig, ax = plt.subplots(figsize=(15,6))
    ax.plot(dates, curve, linewidth=3)

    span_start, span_end = dates[0], dates[-1]

    # Plot confirmed and applicable temporary crew windows
    span_windows = get_windows_for_span(span_start, span_end)
    for w in span_windows:
        ax.axvspan(w["start"], w["end"], alpha=0.15, color="blue")

    if show_deadline:
        ax.axvline(deadline_date, color="red", linewidth=3)

    colors = ["green", "orange", "purple", "blue"]
    for task, comp, color in zip(tasks, completion_dates, colors):
        ax.axvline(comp, linestyle="--", color=color)
        ax.text(comp, max(curve)*0.1, f"{task} Done\n{comp}", rotation=90, fontsize=9, color=color, fontweight="bold")

    ax.scatter(dates[0], curve[0], s=100, color="black")
    ax.scatter(dates[-1], curve[-1], s=100, color="black")

    ax.set_title(title, fontweight="bold")
    ax.set_ylabel("Items Completed")
    ax.set_xlabel("Date")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig

# =====================================================
# DISPLAY GRAPHS
# =====================================================
st.subheader("Span 7–21 Remaining Projection")
st.pyplot(plot_span(span1_dates, span1_curve, span1_tasks, span1_completion, "Span 7–21 Production", True))

st.subheader("Span 22–36B Remaining Projection")
st.pyplot(plot_span(span2_dates, span2_curve, span2_tasks, span2_completion, "Span 22–36B Production", False))

st.sidebar.markdown("---")
st.sidebar.write(f"Span 7–21 Finish: {span1_finish}")
st.sidebar.write(f"Span 22–36B Finish: {span2_finish}")
