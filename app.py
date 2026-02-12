import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

# ============================================
# USER INPUTS
# ============================================

st.sidebar.header("Production Inputs")

start_date = st.sidebar.date_input("Start Date", datetime(2026, 3, 1))
deadline_date = st.sidebar.date_input("Deadline", datetime(2026, 6, 1))

base_crews = st.sidebar.number_input("Base Crews", 1, 10, 2)

rate_per_crew = [
    st.sidebar.number_input("Stringers / Crew / Day", 0.1, 50.0, 8.0),
    st.sidebar.number_input("Cross Frames / Crew / Day", 0.1, 50.0, 6.0),
    st.sidebar.number_input("Cross Girders / Crew / Day", 0.1, 20.0, 1.5),
    st.sidebar.number_input("NB Stringers / Crew / Day", 0.1, 50.0, 8.0),
]

st.sidebar.markdown("---")
st.sidebar.header("Temporary Crew Window")

crews = st.sidebar.number_input("Temporary Crews", 0, 10, 0)

window_start_date = st.sidebar.date_input("Window Start", start_date)
window_duration = st.sidebar.number_input("Window Duration (Work Days)", 0, 60, 0)

# ============================================
# CONSTANT QUANTITIES
# ============================================

stringers_7_21 = 852
cross_frames_7_21 = 82
cross_girders_7_21 = 22

stringers_22_36 = 730

# ============================================
# UTILITY FUNCTIONS
# ============================================

def add_workdays(start, days):
    current = start
    count = 0
    while count < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            count += 1
    return current

def build_span(start, quantities, rates, crews, window_start=None, window_end=None, temp_crews=0):

    dates = []
    curve = []
    completion_dates = []

    remaining = quantities.copy()
    current = start
    total_complete = 0

    while sum(remaining) > 0:

        if current.weekday() < 5:

            multiplier = crews

            if temp_crews > 0 and window_start and window_end:
                if window_start <= current <= window_end:
                    multiplier += temp_crews

            for i in range(len(remaining)):
                if remaining[i] > 0:
                    produced = rates[i] * multiplier
                    produced = min(produced, remaining[i])
                    remaining[i] -= produced
                    total_complete += produced

                    if remaining[i] <= 0:
                        completion_dates.append(current)

        dates.append(current)
        curve.append(total_complete)
        current += timedelta(days=1)

    return dates, curve, completion_dates, current

# ============================================
# BUILD TEMP WINDOW DATES
# ============================================

window_end_date = None
if crews > 0 and window_duration > 0:
    window_end_date = add_workdays(window_start_date, window_duration)

# ============================================
# BUILD SPAN 7-21
# ============================================

span1_quantities = np.array([
    stringers_7_21,
    cross_frames_7_21,
    cross_girders_7_21
])

span1_rates = np.array(rate_per_crew[:3])

span1_dates, span1_curve, span1_completion, span1_finish = build_span(
    start_date,
    span1_quantities,
    span1_rates,
    base_crews,
    window_start_date,
    window_end_date,
    crews
)

# ============================================
# BUILD SPAN 22-36NB
# ============================================

span2_quantities = np.array([stringers_22_36])
span2_rates = np.array([rate_per_crew[3]])

span2_dates, span2_curve, span2_completion, span2_finish = build_span(
    span1_finish,
    span2_quantities,
    span2_rates,
    base_crews,
    window_start_date,
    window_end_date,
    crews
)

# ============================================
# WINDOW SEGMENT LOGIC
# ============================================

crew_windows_span1 = []
crew_windows_span2 = []

if crews > 0 and window_duration > 0:

    span1_start = span1_dates[0]
    span1_end = span1_dates[-1]

    span2_start = span2_dates[0]
    span2_end = span2_dates[-1]

    # Case 1: Entirely in Span 1
    if window_end_date <= span1_end:
        crew_windows_span1.append({
            "start": window_start_date,
            "end": window_end_date
        })

    # Case 2: Entirely in Span 2
    elif window_start_date >= span2_start:
        crew_windows_span2.append({
            "start": window_start_date,
            "end": window_end_date
        })

    # Case 3: Spans Both
    elif window_start_date < span1_end and window_end_date > span1_end:

        crew_windows_span1.append({
            "start": window_start_date,
            "end": span1_end
        })

        crew_windows_span2.append({
            "start": span1_end,
            "end": window_end_date
        })

# ============================================
# PLOTTING FUNCTION
# ============================================

def plot_span(dates, curve, completion_dates, title, crew_windows, show_deadline):

    fig, ax = plt.subplots(figsize=(16,6))
    ax.plot(dates, curve, linewidth=3)

    # Window highlight
    for w in crew_windows:
        ax.axvspan(w["start"], w["end"], alpha=0.2)

    if show_deadline:
        ax.axvline(deadline_date, color="red", linewidth=3)

    for comp in completion_dates:
        ax.axvline(comp, linestyle="--")

    ax.set_title(title, fontweight="bold")
    ax.set_ylabel("Items Completed")
    ax.set_xlabel("Date")
    ax.grid(True, alpha=0.3)

    return fig

# ============================================
# DISPLAY
# ============================================

st.title("FM Projections – Production Timeline")

col1, col2 = st.columns(2)

with col1:
    st.pyplot(
        plot_span(
            span1_dates,
            span1_curve,
            span1_completion,
            "Span 7-21 Production",
            crew_windows_span1,
            show_deadline=True
        )
    )

with col2:
    st.pyplot(
        plot_span(
            span2_dates,
            span2_curve,
            span2_completion,
            "Span 22-36NB Production",
            crew_windows_span2,
            show_deadline=False
        )
    )
