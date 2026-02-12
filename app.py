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
start_date = np.datetime64(today, "D")
if not np.is_busday(start_date):
    start_date = np.busday_offset(start_date, 0, roll="forward")

# =====================================================
# SESSION STATE (temp window)
# =====================================================
if "temp_applied" not in st.session_state:
    st.session_state.temp_applied = False
if "temp_start" not in st.session_state:
    st.session_state.temp_start = today
if "temp_end" not in st.session_state:
    st.session_state.temp_end = today + dt.timedelta(days=14)
if "temp_crews" not in st.session_state:
    st.session_state.temp_crews = 3

# =====================================================
# SIDEBAR INPUTS
# =====================================================
st.sidebar.subheader("Span 7–21 Completed")
c_s1 = st.sidebar.number_input("Stringers Completed (7–21)", 0, TOTALS_SPAN1["Stringers"], 0, key="c_s1")
c_cf1 = st.sidebar.number_input("Cross Frames Completed (7–21)", 0, TOTALS_SPAN1["Cross Frames"], 0, key="c_cf1")
c_cg1 = st.sidebar.number_input("Cross Girders Completed (7–21)", 0, TOTALS_SPAN1["Cross Girders"], 0, key="c_cg1")

st.sidebar.subheader("Span 22–36B Completed")
c_s2 = st.sidebar.number_input("Stringers Completed (22–36B)", 0, TOTALS_SPAN2["Stringers"], 0, key="c_s2")
c_p2 = st.sidebar.number_input("Portals Completed", 0, TOTALS_SPAN2["Portals"], 0, key="c_p2")

st.sidebar.subheader("Production Rates (per day for 2 crews)")
stringers_rate = st.sidebar.number_input("Stringers rate", 0.1, value=16.0, key="stringers_rate")
cross_frames_rate = st.sidebar.number_input("Cross Frames rate", 0.1, value=10.0, key="cross_frames_rate")
cross_girders_rate = st.sidebar.number_input("Cross Girders rate", 0.1, value=1.5, key="cross_girders_rate")
portals_rate = st.sidebar.number_input("Portals rate", 0.1, value=2.0, key="portals_rate")

base_crews = st.sidebar.number_input("Base Crews", 1, value=2, key="base_crews")
deadline_input = st.sidebar.date_input("Deadline (Span 7–21)", dt.date(today.year, 4, 30), key="deadline_input")

# =====================================================
# TEMP CREW ADJUSTMENT WINDOW (confirm + reset)
# =====================================================
st.sidebar.subheader("Temporary Crew Adjustment Window")

enable_temp = st.sidebar.checkbox("Enable Temporary Crew Change", key="enable_temp")

if enable_temp:
    temp_start_ui = st.sidebar.date_input(
        "Change Start Date",
        st.session_state.temp_start,
        key="temp_start_ui",
    )
    temp_end_ui = st.sidebar.date_input(
        "Change End Date",
        st.session_state.temp_end,
        key="temp_end_ui",
    )
    temp_crews_ui = st.sidebar.number_input(
        "Crews During Window",
        1,
        value=int(st.session_state.temp_crews),
        key="temp_crews_ui",
    )

    colA, colB = st.sidebar.columns(2)
    if colA.button("✅ Confirm", key="confirm_temp"):
        # Normalize if user swapped dates
        if temp_end_ui < temp_start_ui:
            temp_start_ui, temp_end_ui = temp_end_ui, temp_start_ui

        st.session_state.temp_start = temp_start_ui
        st.session_state.temp_end = temp_end_ui
        st.session_state.temp_crews = int(temp_crews_ui)
        st.session_state.temp_applied = True
        st.rerun()

    if colB.button("🔄 Reset", key="reset_temp"):
        st.session_state.temp_applied = False
        st.rerun()
else:
    # If user turns off temp mode, wipe it from the graphs/schedule immediately
    if st.session_state.temp_applied:
        st.session_state.temp_applied = False
        st.rerun()

# =====================================================
# HELPERS
# =====================================================
def ensure_busday(d):
    d = np.datetime64(d, "D")
    if not np.is_busday(d):
        d = np.busday_offset(d, 0, roll="forward")
    return d

def to_pydate(d):
    return dt.date.fromisoformat(str(np.datetime64(d, "D")))

def overlap_window(x_min, x_max, w_start, w_end):
    """Returns the overlap interval [a,b] if overlaps else None."""
    a = max(x_min, w_start)
    b = min(x_max, w_end)
    if a <= b:
        return a, b
    return None

# =====================================================
# REMAINING QUANTITIES
# =====================================================
r_s1 = max(TOTALS_SPAN1["Stringers"] - c_s1, 0)
r_cf1 = max(TOTALS_SPAN1["Cross Frames"] - c_cf1, 0)
r_cg1 = max(TOTALS_SPAN1["Cross Girders"] - c_cg1, 0)

r_s2 = max(TOTALS_SPAN2["Stringers"] - c_s2, 0)
r_p2 = max(TOTALS_SPAN2["Portals"] - c_p2, 0)

# Convert rates to per-crew (inputs are per day for 2 crews)
per_crew_rates_span1 = np.array([stringers_rate, cross_frames_rate, cross_girders_rate], dtype=float) / 2.0
per_crew_rates_span2 = np.array([stringers_rate, portals_rate], dtype=float) / 2.0

# =====================================================
# BUILD SCHEDULE
# =====================================================
def build_schedule(tasks, quantities, per_crew_rates, start_dt64):
    remaining = np.array(quantities, dtype=float)
    cumulative = [0.0]
    dates = [ensure_busday(start_dt64)]
    completion_dates = []

    current_day = ensure_busday(start_dt64)
    task_index = 0

    # Temp window settings (only if confirmed/applied)
    temp_on = bool(st.session_state.temp_applied)
    w_start = st.session_state.temp_start if temp_on else None
    w_end = st.session_state.temp_end if temp_on else None
    w_crews = st.session_state.temp_crews if temp_on else None

    while task_index < len(tasks) and remaining.sum() > 0:
        current_day = ensure_busday(current_day)

        if temp_on and (w_start <= to_pydate(current_day) <= w_end):
            crews_today = w_crews
        else:
            crews_today = base_crews

        daily_rate = float(per_crew_rates[task_index]) * float(crews_today)
        completed_today = min(daily_rate, remaining[task_index])

        remaining[task_index] -= completed_today
        cumulative.append(cumulative[-1] + completed_today)

        if remaining[task_index] <= 1e-9:
            completion_dates.append(current_day)
            task_index += 1

        current_day = np.busday_offset(current_day, 1)
        dates.append(current_day)

    return dates, cumulative, completion_dates

# =====================================================
# PLOT FUNCTION
# =====================================================
def plot_span(dates, curve, tasks, completion_dates, title, show_deadline=False, deadline_date=None, y_offset=0.0):
    x = [to_pydate(d) for d in dates]
    y = [v + y_offset for v in curve]

    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(x, y, linewidth=3)

    # Shade temp window only if confirmed + overlaps the plot's date range
    if st.session_state.temp_applied:
        w_start = st.session_state.temp_start
        w_end = st.session_state.temp_end
        x_min, x_max = min(x), max(x)
        ov = overlap_window(x_min, x_max, w_start, w_end)
        if ov:
            a, b = ov
            ax.axvspan(a, b, alpha=0.18)
            ax.text(
                a,
                max(y) * 0.95 if max(y) > 0 else 0.0,
                f"Temp crews: {st.session_state.temp_crews}",
                fontsize=9,
                fontweight="bold",
                va="top",
            )

    colors = ["green", "orange", "purple", "blue"]

    # Completion vertical lines + single-line labels
    label_y = (max(y) * 0.1) if max(y) > 0 else 0.0
    for task, comp, color in zip(tasks, completion_dates, colors):
        comp_py = to_pydate(comp)
        ax.axvline(comp_py, linestyle="--", color=color)
        ax.text(
            comp_py,
            label_y,
            f"{task} Complete: {comp_py.strftime('%m/%d/%Y')}",
            rotation=90,
            fontsize=9,
            color=color,
            fontweight="bold",
            va="bottom",
        )

    if show_deadline and deadline_date is not None:
        ax.axvline(deadline_date, color="red", linewidth=3)

    ax.set_title(title, fontweight="bold")
    ax.set_ylabel("Items Completed")
    ax.set_xlabel("Date")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig

# =====================================================
# RUN PROJECTIONS
# =====================================================
# Span 7–21
span1_tasks = ["Stringers", "Cross Frames", "Cross Girders"]
span1_dates, span1_curve, span1_completion = build_schedule(
    span1_tasks,
    [r_s1, r_cf1, r_cg1],
    per_crew_rates_span1,
    start_date,
)

# End point / finish date for Span 7–21
span1_finish_date = span1_completion[-1] if span1_completion else ensure_busday(start_date)
span1_end_value = span1_curve[-1] if len(span1_curve) else 0.0  # items completed on span 1 plot

# Span 22–36B starts at the ending point/date of Span 7–21
span2_tasks = ["Stringers", "Portals"]
span2_dates, span2_curve, span2_completion = build_schedule(
    span2_tasks,
    [r_s2, r_p2],
    per_crew_rates_span2,
    span1_finish_date,
)

# =====================================================
# DISPLAY
# =====================================================
st.subheader("Span 7–21 Projection")
st.pyplot(
    plot_span(
        span1_dates,
        span1_curve,
        span1_tasks,
        span1_completion,
        "Span 7–21 Production",
        show_deadline=True,
        deadline_date=deadline_input,
        y_offset=0.0,
    )
)

st.subheader("Span 22–36B Projection")
st.pyplot(
    plot_span(
        span2_dates,
        span2_curve,
        span2_tasks,
        span2_completion,
        "Span 22–36B Production",
        show_deadline=False,     # ✅ deadline line removed here
        deadline_date=None,
        y_offset=span1_end_value # ✅ starts at end point of Span 7–21 curve
    )
)
