import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt

st.set_page_config(page_title="FM Projections", layout="wide")
st.title("📊 FM Projections - Production Timeline")

# =====================================================
# TRUE TOTAL JOB QUANTITIES
# =====================================================
TOTALS_SPAN1 = {
    "Stringers": 1023,
    "Cross Frames": 130,
    "Cross Girders": 28
}

TOTALS_SPAN2 = {
    "Stringers": 2429,
    "Portals": 16
}

# =====================================================
# START DATE (BUSINESS DAY)
# =====================================================
today = dt.date.today()
start_date = np.datetime64(today)
if not np.is_busday(start_date):
    start_date = np.busday_offset(start_date, 0, roll="forward")

# =====================================================
# SIDEBAR – COMPLETED INPUTS
# =====================================================
st.sidebar.subheader("Span 7–21 Completed So Far")

completed_stringers_7_21 = st.sidebar.number_input(
    "Stringers Completed (7–21)",
    0, TOTALS_SPAN1["Stringers"], 0
)

completed_cross_frames_7_21 = st.sidebar.number_input(
    "Cross Frames Completed (7–21)",
    0, TOTALS_SPAN1["Cross Frames"], 0
)

completed_cross_girders_7_21 = st.sidebar.number_input(
    "Cross Girders Completed (7–21)",
    0, TOTALS_SPAN1["Cross Girders"], 0
)

st.sidebar.subheader("Span 22–36B Completed So Far")

completed_stringers_22_36B = st.sidebar.number_input(
    "Stringers Completed (22–36B)",
    0, TOTALS_SPAN2["Stringers"], 0
)

completed_portals_22_36B = st.sidebar.number_input(
    "Portals Completed",
    0, TOTALS_SPAN2["Portals"], 0
)

# =====================================================
# CALCULATE REMAINING
# =====================================================
stringers_7_21 = TOTALS_SPAN1["Stringers"] - completed_stringers_7_21
cross_frames_7_21 = TOTALS_SPAN1["Cross Frames"] - completed_cross_frames_7_21
cross_girders_7_21 = TOTALS_SPAN1["Cross Girders"] - completed_cross_girders_7_21

stringers_22_36B = TOTALS_SPAN2["Stringers"] - completed_stringers_22_36B
portals_22_36B = TOTALS_SPAN2["Portals"] - completed_portals_22_36B

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
st.sidebar.subheader("Base Crews")
base_crews = st.sidebar.number_input("Base Number of Crews", 1, value=2)

# =====================================================
# DEADLINE
# =====================================================
st.sidebar.subheader("Deadline")
deadline_input = st.sidebar.date_input("Deadline Date", dt.date(today.year, 4, 30))
deadline_date = np.datetime64(deadline_input)

# =====================================================
# TEMPORARY WINDOWS (unchanged)
# =====================================================
st.sidebar.subheader("Temporary Crew Windows")
num_windows = st.sidebar.number_input("Number of Windows", 0, 5, 0)

if "confirmed_windows" not in st.session_state:
    st.session_state.confirmed_windows = {}

crew_windows = []

for i in range(int(num_windows)):

    st.sidebar.markdown("---")
    crews = st.sidebar.number_input(
        f"Crews During Window {i+1}",
        min_value=1,
        value=base_crews + 1,
        key=f"crews_{i}"
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

for w in st.session_state.confirmed_windows.values():
    crew_windows.append(w)

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

    while task_index < len(tasks):

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
# BUILD SPANS (using REMAINING quantities)
# =====================================================
span1_tasks = ["Stringers", "Cross Frames", "Cross Girders"]
span1_quantities = np.array([
    stringers_7_21,
    cross_frames_7_21,
    cross_girders_7_21
])

span1_dates, span1_curve, span1_completion = build_schedule(
    span1_tasks, span1_quantities, rate_per_crew[:3], start_date
)

span1_finish = span1_completion[-1] if span1_completion else start_date

span2_tasks = ["Stringers", "Portals"]
span2_quantities = np.array([
    stringers_22_36B,
    portals_22_36B
])

span2_dates, span2_curve, span2_completion = build_schedule(
    span2_tasks,
    span2_quantities,
    np.array([rate_per_crew[0], rate_per_crew[3]]),
    np.busday_offset(span1_finish, 1)
)

span2_finish = span2_completion[-1] if span2_completion else span1_finish

# =====================================================
# PLOTTING (unchanged)
# =====================================================
def plot_span(dates, curve, tasks, completion_dates, title, show_deadline=True):

    fig, ax = plt.subplots(figsize=(15,6))
    ax.plot(dates, curve, linewidth=3)

    for w in crew_windows:
        ax.axvspan(w["start"], w["end"], alpha=0.15)

    if show_deadline:
        ax.axvline(deadline_date, color="red", linewidth=3)

    for task, comp in zip(tasks, completion_dates):
        ax.axvline(comp, linestyle="--")

    ax.set_title(title, fontweight="bold")
    ax.set_ylabel("Items Completed")
    ax.set_xlabel("Date")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    return fig

# =====================================================
# DISPLAY
# =====================================================
st.subheader("Span 7–21 Remaining Work Projection")
st.pyplot(plot_span(
    span1_dates, span1_curve,
    span1_tasks, span1_completion,
    "Span 7–21 Remaining Work Projection",
    show_deadline=True
))

st.subheader("Span 22–36B Remaining Work Projection")
st.pyplot(plot_span(
    span2_dates, span2_curve,
    span2_tasks, span2_completion,
    "Span 22–36B Remaining Work Projection",
    show_deadline=False
))

st.sidebar.markdown("---")
st.sidebar.write(f"Span 7–21 Finish: {span1_finish}")
st.sidebar.write(f"Span 22–36B Finish: {span2_finish}")
