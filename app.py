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
# SIDEBAR QUANTITIES
# ==========================
st.sidebar.subheader("Span 7–21 Quantities (each)")

for key, val in {
    "Stringers_7_21": default_span1["Stringers"],
    "Cross Frames_7_21": default_span1["Cross Frames"],
    "Cross Girders_7_21": default_span1["Cross Girders"]
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

stringers_7_21 = st.sidebar.number_input("Stringers (7–21)", min_value=0, step=1, key="Stringers_7_21")
cross_frames_7_21 = st.sidebar.number_input("Cross Frames (7–21)", min_value=0, step=1, key="Cross Frames_7_21")
cross_girders_7_21 = st.sidebar.number_input("Cross Girders (7–21)", min_value=0, step=1, key="Cross Girders_7_21")

st.sidebar.subheader("Span 22–36B Quantities (each)")

for key, val in {
    "Stringers_22_36B": default_span2["Stringers"],
    "Portals_22_36B": default_span2["Portals"]
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

stringers_22_36B = st.sidebar.number_input("Stringers (22–36B)", min_value=0, step=1, key="Stringers_22_36B")
portals_22_36B = st.sidebar.number_input("Portals (22–36B)", min_value=0, step=1, key="Portals_22_36B")

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
# WINDOW IMPACT FUNCTION
# ==========================
def calculate_window_impact(start, end, base_crews, window_crews, rate_per_crew):
    business_days = np.busday_count(start, end + np.timedelta64(1, 'D'))
    base_daily_total = np.sum(rate_per_crew) * base_crews
    window_daily_total = np.sum(rate_per_crew) * window_crews
    base_total = base_daily_total * business_days
    window_total = window_daily_total * business_days
    gain = window_total - base_total
    return business_days, base_total, window_total, gain

# ==========================
# TEMPORARY CREW WINDOWS
# ==========================
st.sidebar.subheader("Temporary Crew Windows")
num_windows = st.sidebar.number_input("Number of Temporary Crew Windows", min_value=0, value=0, step=1)

if 'confirmed_windows' not in st.session_state:
    st.session_state.confirmed_windows = {}

crew_windows = []

for i in range(int(num_windows)):
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Window {i+1}**")

    crews = st.sidebar.number_input(
        f"Crews During Window {i+1}",
        min_value=1,
        value=base_crews+1,
        step=1,
        key=f"crews_{i}"
    )

    start = st.sidebar.date_input(f"Start Date {i+1}", value=today, key=f"start_{i}")
    end = st.sidebar.date_input(f"End Date {i+1}", value=today+dt.timedelta(days=14), key=f"end_{i}")

    if start < today:
        start = today
    if end <= start:
        end = start + dt.timedelta(days=1)

    if st.sidebar.button(f"Confirm Window {i+1}", key=f"confirm_{i}"):

        start_np = np.datetime64(start)
        end_np = np.datetime64(end)

        st.session_state.confirmed_windows[i] = {
            "crews": crews,
            "start": start_np,
            "end": end_np
        }

        business_days, base_total, window_total, gain = calculate_window_impact(
            start_np,
            end_np,
            base_crews,
            crews,
            rate_per_crew
        )

        st.sidebar.success("✅ Window Confirmed")
        st.sidebar.markdown("### 📈 Window Production Impact")
        st.sidebar.write(f"Business Days: **{business_days}**")
        st.sidebar.write(f"Production with {base_crews} crews: **{int(base_total)} items**")
        st.sidebar.write(f"Production with {crews} crews: **{int(window_total)} items**")

        if gain > 0:
            st.sidebar.write(f"🚀 Net Gain: **+{int(gain)} items**")
        else:
            st.sidebar.write("No production increase.")

for w in st.session_state.confirmed_windows.values():
    crew_windows.append(w)

crew_windows = sorted(crew_windows, key=lambda x: x["start"])

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

# ==========================
# SPAN 7–21
# ==========================
span1_tasks = ["Stringers", "Cross Frames", "Cross Girders"]
span1_quantities = np.array([stringers_7_21, cross_frames_7_21, cross_girders_7_21])

span1_dates, span1_curve, span1_completion = build_schedule(
    span1_quantities,
    rate_per_crew[:3],
    base_crews,
    crew_windows,
    start_date
)

span1_finish = span1_completion[-1]

# ==========================
# SPAN 22–36B
# ==========================
span2_start = np.busday_offset(span1_finish, 1)
span2_tasks = ["Stringers", "Portals"]
span2_quantities = np.array([stringers_22_36B, portals_22_36B])
span2_rates = np.array([rate_per_crew[0], rate_per_crew[3]])

span2_dates, span2_curve, span2_completion = build_schedule(
    span2_quantities,
    span2_rates,
    base_crews,
    crew_windows,
    span2_start
)

span2_finish = span2_completion[-1]

# ==========================
# PLOT
# ==========================
def plot_span(dates, curve, tasks, completion_dates, title, deadline=None):
    fig, ax = plt.subplots(figsize=(14,6))
    ax.plot(dates, curve, linewidth=3, marker="o", markersize=4)

    if deadline is not None:
        ax.axvline(deadline, color="red", linewidth=3)

    ax.set_title(title, fontweight="bold")
    ax.set_ylabel("Items Completed")
    ax.set_xlabel("Date")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig

st.subheader("Span 7–21 Production Timeline")
st.pyplot(plot_span(span1_dates, span1_curve, span1_tasks, span1_completion,
                    "Span 7–21 Production Timeline", deadline=deadline_date))

st.subheader("Span 22–36B Production Timeline")
st.pyplot(plot_span(span2_dates, span2_curve, span2_tasks, span2_completion,
                    "Span 22–36B Production Timeline"))

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Completion Dates")
st.sidebar.write(f"Span 7–21 Finish: {span1_finish}")
st.sidebar.write(f"Span 22–36B Finish: {span2_finish}")
