import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt

st.set_page_config(page_title="FM Projections", layout="wide")
st.title("📊 FM Projections - Production Timeline")

# ==========================
# DEFAULTS
# ==========================
default_span1 = {"Stringers": 852, "Cross Frames": 82, "Cross Girders": 22}
default_span2 = {"Stringers": 1369, "Portals": 8}

# ==========================
# AUTO START DATE (TODAY)
# ==========================
today = dt.date.today()
start_date = np.datetime64(today)
if not np.is_busday(start_date):
    start_date = np.busday_offset(start_date, 0, roll='forward')

# ==========================
# SIDEBAR QUANTITIES WITH INDIVIDUAL RESET BUTTONS
# ==========================
st.sidebar.subheader("Span 7–21 Quantities (each)")

stringers_7_21 = st.sidebar.number_input(
    "Stringers (7–21)", min_value=0, step=1,
    value=st.session_state.get("Stringers_7_21", default_span1["Stringers"]),
    key="Stringers_7_21"
)
if st.sidebar.button("Reset Stringers 7–21"):
    st.session_state["Stringers_7_21"] = default_span1["Stringers"]

cross_frames_7_21 = st.sidebar.number_input(
    "Cross Frames (7–21)", min_value=0, step=1,
    value=st.session_state.get("Cross Frames_7_21", default_span1["Cross Frames"]),
    key="Cross Frames_7_21"
)
if st.sidebar.button("Reset Cross Frames 7–21"):
    st.session_state["Cross Frames_7_21"] = default_span1["Cross Frames"]

cross_girders_7_21 = st.sidebar.number_input(
    "Cross Girders (7–21)", min_value=0, step=1,
    value=st.session_state.get("Cross Girders_7_21", default_span1["Cross Girders"]),
    key="Cross Girders_7_21"
)
if st.sidebar.button("Reset Cross Girders 7–21"):
    st.session_state["Cross Girders_7_21"] = default_span1["Cross Girders"]

st.sidebar.subheader("Span 22–36B Quantities (each)")

stringers_22_36B = st.sidebar.number_input(
    "Stringers (22–36B)", min_value=0, step=1,
    value=st.session_state.get("Stringers_22_36B", default_span2["Stringers"]),
    key="Stringers_22_36B"
)
if st.sidebar.button("Reset Stringers 22–36B"):
    st.session_state["Stringers_22_36B"] = default_span2["Stringers"]

portals_22_36B = st.sidebar.number_input(
    "Portals (22–36B)", min_value=0, step=1,
    value=st.session_state.get("Portals_22_36B", default_span2["Portals"]),
    key="Portals_22_36B"
)
if st.sidebar.button("Reset Portals 22–36B"):
    st.session_state["Portals_22_36B"] = default_span2["Portals"]

# ==========================
# PRODUCTION RATES
# ==========================
st.sidebar.subheader("Production Rates (per day for 2 crews)")
stringers_rate = st.sidebar.number_input("Stringers rate", min_value=0.1, value=16.0, step=0.5)
cross_frames_rate = st.sidebar.number_input("Cross Frames rate", min_value=0.1, value=10.0, step=0.5)
cross_girders_rate = st.sidebar.number_input("Cross Girders rate", min_value=0.1, value=1.5, step=0.5)
portals_rate = st.sidebar.number_input("Portals rate", min_value=0.1, value=2.0, step=0.5)
rates_2_crews = np.array([stringers_rate, cross_frames_rate, cross_girders_rate, portals_rate])
rate_per_crew = rates_2_crews / 2

# ==========================
# BASE CREWS
# ==========================
st.sidebar.subheader("Base Crew Configuration")
base_crews = st.sidebar.number_input("Base Number of Crews", min_value=1, value=2, step=1)

# ==========================
# DEADLINE
# ==========================
st.sidebar.subheader("Project Deadline")
default_deadline = dt.date(today.year, 4, 30)
deadline_input = st.sidebar.date_input("Deadline Date", value=default_deadline)
deadline_date = np.datetime64(deadline_input)

# ==========================
# TEMPORARY CREW WINDOWS
# ==========================
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

    if start < today:
        start = today
        st.sidebar.warning(f"Window {i+1}: Start date adjusted to today.")
    if end <= start:
        end = start + dt.timedelta(days=1)

    start_str = start.strftime("%A, %B %d, %Y")
    end_str = end.strftime("%A, %B %d, %Y")
    st.sidebar.info(f"Temporary crew window will start **{start_str}** and finish **{end_str}**.")

    if st.sidebar.button(f"Confirm Window {i+1}", key=f"confirm_{i}"):
        st.session_state.confirmed_windows[i] = {"crews": crews, "start": np.datetime64(start), "end": np.datetime64(end)}

for w in st.session_state.confirmed_windows.values():
    crew_windows.append(w)

crew_windows = sorted(crew_windows, key=lambda x: x["start"])
for i in range(len(crew_windows)-1):
    if crew_windows[i]["end"] > crew_windows[i+1]["start"]:
        crew_windows[i+1]["start"] = np.busday_offset(crew_windows[i]["end"], 1)

# ==========================
# CREW LOOKUP
# ==========================
def get_crews_for_day(day, base_crews, windows):
    crews_today = base_crews
    for w in windows:
        if w["start"] <= day <= w["end"]:
            crews_today = w["crews"]
    return crews_today

# ==========================
# SCHEDULER
# ==========================
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
        if remaining[task_index] <= 0:
            completion_dates.append(None)
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
            completion_dates.append(current_day)
            task_index += 1

        current_day = np.busday_offset(current_day, 1)
        dates.append(current_day)

    return dates, cumulative, completion_dates

def adjust_windows_for_next_span(windows, next_span_start):
    adjusted = []
    for w in windows:
        if w["end"] < next_span_start:
            continue
        new_start = max(w["start"], next_span_start)
        adjusted.append({"crews": w["crews"], "start": new_start, "end": w["end"]})
    return adjusted

# ==========================
# SPAN 7–21
# ==========================
span1_tasks = ["Stringers", "Cross Frames", "Cross Girders"]
span1_quantities = np.array([stringers_7_21, cross_frames_7_21, cross_girders_7_21])

if np.all(span1_quantities == 0):
    st.success("✅ Span 7–21 is already complete!")
    span1_dates = [start_date]
    span1_curve = [0]
    span1_completion = [start_date]
    span1_finish = start_date
else:
    span1_dates, span1_curve, span1_completion = build_schedule(
        span1_quantities, rate_per_crew[:3], base_crews, crew_windows, start_date
    )
    span1_finish = span1_completion[-1]

# ==========================
# SPAN 22–36B
# ==========================
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

# ==========================
# PLOT FUNCTION
# ==========================
def plot_span(dates, curve, tasks, completion_dates, title, deadline=None, windows=None, clip_end=None):
    fig, ax = plt.subplots(figsize=(14,6))
    ax.plot(dates, curve, linewidth=3, marker="o", markersize=4)

    if deadline is not None:
        ax.axvline(deadline, color="red", linewidth=3)
        ax.text(deadline, max(curve)*0.9, "DEADLINE", rotation=90, color="red", fontweight="bold", va="top")

    colors = ["green", "orange", "purple", "blue"]
    for i, (task, comp_date, color) in enumerate(zip(tasks, completion_dates, colors)):
        if comp_date is None:
            continue
        ax.axvline(comp_date, linestyle="--", alpha=0.7, color=color)
        ax.text(comp_date, max(curve)*0.05, f"{task}\n{comp_date}", rotation=90, va="bottom", fontsize=9, fontweight="bold", color=color)

    ax.scatter(dates[0], curve[0], s=120, color="black", zorder=5)
    ax.text(dates[0], curve[0], f"Start\n{dates[0]}", va="bottom", fontsize=9, fontweight="bold")

    last_completion = [d for d in completion_dates if d is not None][-1]
    ax.scatter(last_completion, curve[-1], s=120, color="black", zorder=5)
    ax.text(last_completion, curve[-1], f"Finish\n{last_completion}", va="bottom", fontsize=9, fontweight="bold")

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

# ==========================
# PLOTS
# ==========================
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

# ==========================
# SIDEBAR SUMMARY
# ==========================
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Completion Dates")
st.sidebar.write(f"Span 7–21 Finish: {span1_finish}")
st.sidebar.write(f"Span 22–36B Finish: {span2_finish}")
