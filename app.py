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
if not np.is_busday(start_date):
    start_date = np.busday_offset(start_date, 0, roll='forward')

# =====================================================
# SIDEBAR INPUTS
# =====================================================
st.sidebar.header("Project Parameters")

# -------------------------------
# Span 7–21 Quantities
# -------------------------------
st.sidebar.subheader("Span 7–21 Quantities (each)")
stringers_7_21 = st.sidebar.number_input("Stringers (7–21)", min_value=0, value=852, step=1)
cross_frames_7_21 = st.sidebar.number_input("Cross Frames (7–21)", min_value=0, value=82, step=1)
cross_girders_7_21 = st.sidebar.number_input("Cross Girders (7–21)", min_value=0, value=22, step=1)

# -------------------------------
# Span 22–36B Quantities
# -------------------------------
st.sidebar.subheader("Span 22–36B Quantities (each)")
stringers_22_36B = st.sidebar.number_input("Stringers (22–36B)", min_value=0, value=1369, step=1)
portals_22_36B = st.sidebar.number_input("Portals (22–36B)", min_value=0, value=8, step=1)

# -------------------------------
# Production Rates (per 2 crews)
# -------------------------------
st.sidebar.subheader("Production Rates (per day for 2 crews)")
stringers_rate = st.sidebar.number_input("Stringers rate", min_value=0.1, value=16.0, step=0.5)
cross_frames_rate = st.sidebar.number_input("Cross Frames rate", min_value=0.1, value=10.0, step=0.5)
cross_girders_rate = st.sidebar.number_input("Cross Girders rate", min_value=0.1, value=1.5, step=0.5)
portals_rate = st.sidebar.number_input("Portals rate", min_value=0.1, value=2.0, step=0.5)

rates_2_crews = np.array([stringers_rate, cross_frames_rate, cross_girders_rate, portals_rate])
rate_per_crew = rates_2_crews / 2

# -------------------------------
# Base Crews
# -------------------------------
st.sidebar.subheader("Base Crew Configuration")
base_crews = st.sidebar.number_input("Base Number of Crews", min_value=1, value=2, step=1)

# -------------------------------
# Deadline
# -------------------------------
st.sidebar.subheader("Project Deadline")
default_deadline = dt.date(today.year, 4, 30)
deadline_input = st.sidebar.date_input("Deadline Date", value=default_deadline)
deadline_date = np.datetime64(deadline_input)

# =====================================================
# Temporary Crew Windows with Confirmation
# =====================================================
st.sidebar.subheader("Temporary Crew Windows")
num_windows = st.sidebar.number_input("Number of Temporary Crew Windows", min_value=0, value=0, step=1)
crew_windows = []

if 'confirmed_windows' not in st.session_state:
    st.session_state.confirmed_windows = {}

for i in range(int(num_windows)):
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Window {i+1}**")
    crews = st.sidebar.number_input(f"Crews During Window {i+1}", min_value=1, value=base_crews+1, step=1, key=f"crews_{i}")
    
    start = st.sidebar.date_input(f"Start Date {i+1}", value=today, key=f"start_{i}")
    end = st.sidebar.date_input(f"End Date {i+1}", value=today+dt.timedelta(days=14), key=f"end_{i}")

    # Ensure start date is not before today
    if start < today:
        start = today
        st.sidebar.warning(f"Window {i+1}: Start date adjusted to today since it cannot be in the past.")

    # Automatically fix end date if before start
    if end <= start:
        end = start + dt.timedelta(days=1)

    # Show start/end with day of week
    start_str = start.strftime("%A, %B %d, %Y")
    end_str = end.strftime("%A, %B %d, %Y")
    st.sidebar.info(f"Temporary crew window will start **{start_str}** and finish **{end_str}**.")

    # Confirm button
    if st.sidebar.button(f"Confirm Window {i+1}", key=f"confirm_{i}"):
        st.session_state.confirmed_windows[i] = {"crews": crews, "start": np.datetime64(start), "end": np.datetime64(end)}

# Collect confirmed windows
for w in st.session_state.confirmed_windows.values():
    crew_windows.append(w)

# Sort and adjust overlaps automatically
crew_windows = sorted(crew_windows, key=lambda x: x["start"])
for i in range(len(crew_windows)-1):
    if crew_windows[i]["end"] > crew_windows[i+1]["start"]:
        st.sidebar.warning(f"⚠️ Window {i+1} overlaps with Window {i+2}, adjusting next start date automatically.")
        crew_windows[i+1]["start"] = np.busday_offset(crew_windows[i]["end"], 1)

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
# SCHEDULER (BUSINESS DAYS ONLY, zero quantities handled)
# =====================================================
def build_schedule(quantities, rate_per_crew, base_crews, windows, start_date):
    remaining = quantities.copy()
    cumulative = [0]
    dates = [start_date]
    current_day = start_date
    task_index = 0
    completion_dates = []

    if not np.is_busday(current_day):
        current_day = np.busday_offset(current_day, 0, roll='forward')

    while task_index < len(remaining):
        # Skip tasks with 0 quantity
        if remaining[task_index] <= 0:
            completion_dates.append(current_day)
            task_index += 1
            continue

        if not np.is_busday(current_day):
            current_day = np.busday_offset(current_day, 0, roll='forward')

        crews_today = get_crews_for_day(current_day, base_crews, windows)
        daily_rate = rate_per_crew[task_index] * crews_today

        completed = min(daily_rate, remaining[task_index])
        remaining[task_index] -= completed
        cumulative.append(cumulative[-1] + completed)

        if remaining[task_index] <= 0:
            if not np.is_busday(current_day):
                current_day = np.busday_offset(current_day, 0, roll='forward')
            completion_dates.append(current_day)
            task_index += 1

        current_day = np.busday_offset(current_day, 1)
        dates.append(current_day)

    return dates, cumulative, completion_dates

# =====================================================
# Adjust windows for next span
# =====================================================
def adjust_windows_for_next_span(windows, next_span_start):
    adjusted = []
    for w in windows:
        if w["end"] < next_span_start:
            continue
        new_start = max(w["start"], next_span_start)
        adjusted.append({"index": w.get("index",0), "crews": w["crews"], "start": new_start, "end": w["end"]})
    return adjusted

# =====================================================
# SPAN 7–21
# =====================================================
span1_tasks = ["Stringers", "Cross Frames", "Cross Girders"]
span1_quantities = np.array([stringers_7_21, cross_frames_7_21, cross_girders_7_21])

if np.all(span1_quantities == 0):
    st.success("✅ Span 7–21 is already complete (all quantities are 0).")
    span1_dates = [start_date]
    span1_curve = [0]
    span1_completion = [start_date]
    span1_finish = start_date
else:
    span1_dates, span1_curve, span1_completion = build_schedule(
        span1_quantities, rate_per_crew[:3], base_crews, crew_windows, start_date
    )
    span1_finish = span1_completion[-1]

# =====================================================
# SPAN 22–36B
# =====================================================
span2_start = np.busday_offset(span1_finish, 1)
span2_tasks = ["Stringers", "Portals"]
span2_quantities = np.array([stringers_22_36B, portals_22_36B])
span2_rates = np.array([rate_per_crew[0], rate_per_crew[3]])
span2_windows = adjust_windows_for_next_span(crew_windows, span2_start)

if np.all(span2_quantities == 0):
    st.success("✅ All field measurements are complete! No work required for Span 22–36B.")
    span2_dates = [span2_start]
    span2_curve = [0]
    span2_completion = [span2_start]
    span2_finish = span2_start
else:
    span2_dates, span2_curve, span2_completion = build_schedule(
        span2_quantities, span2_rates, base_crews, span2_windows, span2_start
    )
    span2_finish = span2_completion[-1]

# =====================================================
# PLOT FUNCTION
# =====================================================
def plot_span(dates, curve, tasks, completion_dates, title, deadline=None, windows=None, clip_end=None):
    fig, ax = plt.subplots(figsize=(14,6))
    ax.plot(dates, curve, linewidth=3, marker="o", markersize=4)

    if deadline is not None:
        ax.axvline(deadline, color="red", linewidth=3)
        ax.text(deadline, max(curve)*0.9, "DEADLINE", rotation=90, color="red", fontweight="bold", va="top")

    colors = ["green", "orange", "purple", "blue"]
    for task, comp_date, color in zip(tasks, completion_dates, colors):
        ax.axvline(comp_date, linestyle="--", alpha=0.7, color=color)
        ax.text(comp_date, max(curve)*0.05, f"{task}\n{comp_date}", rotation=90, va="bottom", fontsize=9, fontweight="bold", color=color)

    # Start and finish points
    ax.scatter(dates[0], curve[0], s=120, color="black", zorder=5)
    ax.text(dates[0], curve[0], f"Start\n{dates[0]}", va="bottom", fontsize=9, fontweight="bold")
    ax.scatter(completion_dates[-1], curve[-1], s=120, color="black", zorder=5)
    ax.text(completion_dates[-1], curve[-1], f"Finish\n{completion_dates[-1]}", va="bottom", fontsize=9, fontweight="bold")

    # Temporary crew windows
    if windows:
        for w in windows:
            start = w["start"]
            end = w["end"]
            if clip_end is not None:
                end = min(end, clip_end)
            if start > end:
                continue
            ax.axvspan(start, end, color="yellow", alpha=0.2)

    ax.set_title(title, fontweight="bold")
    ax.set_ylabel("Items Completed (each)", fontweight="bold")
    ax.set_xlabel("Date", fontweight="bold")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig

# =====================================================
# PLOTS
# =====================================================
st.subheader("Span 7–21 Production Timeline")
fig1 = plot_span(span1_dates, span1_curve, span1_tasks, span1_completion,
                 "Span 7–21 Production Timeline", deadline=deadline_date, windows=crew_windows, clip_end=span1_finish)
st.pyplot(fig1)

if not np.all(span1_quantities == 0):
    days_before_deadline = int((deadline_date - span1_finish)/np.timedelta64(1,'D'))
    if days_before_deadline >= 0:
        st.success(f"✅ Span 7–21 finishes {days_before_deadline} days BEFORE deadline")
    else:
        st.error(f"⚠️ Span 7–21 finishes {abs(days_before_deadline)} days AFTER deadline")

st.subheader("Span 22–36B Production Timeline")
fig2 = plot_span(span2_dates, span2_curve, span2_tasks, span2_completion,
                 "Span 22–36B Production Timeline", windows=span2_windows)
st.pyplot(fig2)

# =====================================================
# SIDEBAR SUMMARY
# =====================================================
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Completion Dates")
st.sidebar.write(f"Span 7–21 Finish: {span1_finish}")
st.sidebar.write(f"Span 22–36B Finish: {span2_finish}")
