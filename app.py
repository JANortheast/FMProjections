import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdates

st.set_page_config(layout="wide")

# ==========================================================
# DATA
# ==========================================================

start_date = np.datetime64("2026-05-01")
deadline_span1 = np.datetime64("2026-07-01")

tasks_span1 = [
    "Span 7-21 Stringers",
    "Cross Frames",
    "Cross Girders"
]

quantities_span1 = [852, 82, 22]

tasks_span2 = [
    "Span 22-36B Stringers",
    "Portals"
]

quantities_span2 = [694, 24]

# Production per crew per day
rates_span1 = [8, 4, 1.5]
rates_span2 = [8, 1]

# ==========================================================
# SIDEBAR CONTROLS
# ==========================================================

st.sidebar.title("Production Controls")

base_crews = st.sidebar.slider("Base Crews", 1, 6, 2)

use_window = st.sidebar.checkbox("Use Crew Window")

if use_window:
    window_crews = st.sidebar.slider("Window Crews", 1, 8, 4)
    window_start = np.datetime64(st.sidebar.date_input("Window Start"))
    window_end = np.datetime64(st.sidebar.date_input("Window End"))

# ==========================================================
# PRODUCTION CURVE BUILDER
# ==========================================================

def build_curve(tasks, quantities, rates):

    cumulative = []
    dates = []
    task_finish_dates = []
    total_completed = 0
    current_date = start_date

    for task, qty, rate in zip(tasks, quantities, rates):

        completed = 0

        while completed < qty:

            # Determine crews for the day
            if use_window and window_start <= current_date <= window_end:
                crews_today = window_crews
            else:
                crews_today = base_crews

            daily_production = rate * crews_today

            remaining = qty - completed
            actual_today = min(daily_production, remaining)

            completed += actual_today
            total_completed += actual_today

            cumulative.append(total_completed)
            dates.append(current_date)

            current_date = np.busday_offset(current_date, 1, roll='forward')

        task_finish_dates.append((task, current_date))

    return np.array(dates), cumulative, task_finish_dates

# ==========================================================
# GENERATE CURVES
# ==========================================================

dates1, cumulative1, finishes1 = build_curve(tasks_span1, quantities_span1, rates_span1)
dates2, cumulative2, finishes2 = build_curve(tasks_span2, quantities_span2, rates_span2)

# ==========================================================
# PLOTTING
# ==========================================================

col1, col2 = st.columns(2)

# -------------------------
# SPAN 7-21
# -------------------------

with col1:

    fig1, ax1 = plt.subplots(figsize=(11,6))

    ax1.plot(dates1, cumulative1)

    ax1.set_title("Span 7-21 Production")
    ax1.set_ylabel("Cumulative Units")

    # Deadline ONLY here
    ax1.axvline(deadline_span1, linestyle='--')

    # Window shading
    if use_window:
        ax1.axvspan(window_start, window_end, alpha=0.2)

    # Completion lines
    for task, finish_date in finishes1:
        ax1.axvline(finish_date, linestyle=':', alpha=0.6)

    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    fig1.autofmt_xdate()

    st.pyplot(fig1)

# -------------------------
# SPAN 22-36B
# -------------------------

with col2:

    fig2, ax2 = plt.subplots(figsize=(11,6))

    ax2.plot(dates2, cumulative2)

    ax2.set_title("Span 22-36B Production")
    ax2.set_ylabel("Cumulative Units")

    # NO DEADLINE HERE

    # Window shading
    if use_window:
        ax2.axvspan(window_start, window_end, alpha=0.2)

    # Completion lines
    for task, finish_date in finishes2:
        ax2.axvline(finish_date, linestyle=':', alpha=0.6)

    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    fig2.autofmt_xdate()

    st.pyplot(fig2)

# ==========================================================
# WINDOW IMPACT SUMMARY
# ==========================================================

if use_window:

    st.markdown("## 📈 Window Impact Summary")

    business_days = np.busday_count(window_start, window_end + np.timedelta64(1, 'D'))

    # Calculate theoretical production
    base_daily_total = (
        sum(rates_span1) + sum(rates_span2)
    ) * base_crews

    window_daily_total = (
        sum(rates_span1) + sum(rates_span2)
    ) * window_crews

    base_total = base_daily_total * business_days
    window_total = window_daily_total * business_days
    gain = window_total - base_total

    st.write(f"Business Days: {business_days}")
    st.write(f"Production with {base_crews} crews: {int(base_total)} total units")
    st.write(f"Production with {window_crews} crews: {int(window_total)} total units")
    st.write(f"Net Gain: +{int(gain)} units")

    # Determine which items were completed during window
    completed_during_window = []

    for task, finish_date in finishes1 + finishes2:
        if window_start <= finish_date <= window_end:
            completed_during_window.append(task)

    if completed_during_window:
        st.markdown("### Items Completed During Window")
        for item in completed_during_window:
            st.write(f"• {item}")
    else:
        st.write("No items were fully completed during the window.")
