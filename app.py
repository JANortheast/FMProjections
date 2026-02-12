import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import matplotlib.dates as mdates

st.set_page_config(layout="wide")

# =========================
# TASK DATA
# =========================

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

rate_per_crew = np.array([8, 4, 1.5, 8, 1])  # per crew production rates

start_date = np.datetime64("2026-05-01")
deadline_span1 = np.datetime64("2026-07-01")

# =========================
# SIDEBAR INPUTS
# =========================

st.sidebar.title("Production Controls")

base_crews = st.sidebar.slider("Base Crews", 1, 6, 2)

use_window = st.sidebar.checkbox("Use Crew Window")

if use_window:
    window_crews = st.sidebar.slider("Window Crews", 1, 8, 4)
    window_start = np.datetime64(st.sidebar.date_input("Window Start"))
    window_end = np.datetime64(st.sidebar.date_input("Window End"))

# =========================
# BUILD CUMULATIVE CURVE
# =========================

def build_curve(tasks, quantities, rates, crews):
    cumulative = []
    task_finish_dates = []
    total = 0
    current_date = start_date

    for qty, rate in zip(quantities, rates):
        daily = rate * crews
        days = int(np.ceil(qty / daily))

        dates = np.busday_offset(current_date, np.arange(days), roll='forward')
        prod = np.minimum(daily * np.arange(1, days+1), qty)

        cumulative.extend(total + prod)
        total += qty

        finish_date = dates[-1]
        task_finish_dates.append((finish_date, qty))

        current_date = np.busday_offset(finish_date, 1, roll='forward')

    dates_full = np.busday_offset(start_date, np.arange(len(cumulative)), roll='forward')

    return dates_full, cumulative, task_finish_dates

# =========================
# BUILD WINDOW ADJUSTED CURVE
# =========================

def build_curve_with_window(tasks, quantities, rates):
    cumulative = []
    task_finish_dates = []
    total = 0
    current_date = start_date

    for i, (qty, rate) in enumerate(zip(quantities, rates)):
        qty_done = 0

        while qty_done < qty:
            if use_window and window_start <= current_date <= window_end:
                crews = window_crews
            else:
                crews = base_crews

            daily = rate * crews
            qty_done += daily
            total += min(daily, qty - (qty_done - daily))

            cumulative.append(total)

            current_date = np.busday_offset(current_date, 1, roll='forward')

        task_finish_dates.append((current_date, qty))

    dates_full = np.busday_offset(start_date, np.arange(len(cumulative)), roll='forward')

    return dates_full, cumulative, task_finish_dates

# =========================
# GENERATE DATA
# =========================

if use_window:
    d1, c1, f1 = build_curve_with_window(tasks_span1, quantities_span1, rate_per_crew[:3])
    d2, c2, f2 = build_curve_with_window(tasks_span2, quantities_span2, rate_per_crew[3:])
else:
    d1, c1, f1 = build_curve(tasks_span1, quantities_span1, rate_per_crew[:3], base_crews)
    d2, c2, f2 = build_curve(tasks_span2, quantities_span2, rate_per_crew[3:], base_crews)

# =========================
# PLOT
# =========================

col1, col2 = st.columns(2)

# =========================
# SPAN 7-21 GRAPH
# =========================

with col1:
    fig1, ax1 = plt.subplots(figsize=(10,6))

    ax1.plot(d1, c1)
    ax1.set_title("Span 7-21 Production")

    # Deadline only here
    ax1.axvline(deadline_span1, linestyle='--')

    # Window shading
    if use_window:
        ax1.axvspan(window_start, window_end, alpha=0.2)

    # Completion lines
    for date, qty in f1:
        ax1.axvline(date, linestyle=':', alpha=0.5)

    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    fig1.autofmt_xdate()

    st.pyplot(fig1)

# =========================
# SPAN 22-36B GRAPH
# =========================

with col2:
    fig2, ax2 = plt.subplots(figsize=(10,6))

    ax2.plot(d2, c2)
    ax2.set_title("Span 22-36B Production")

    # NO DEADLINE HERE

    # Window shading
    if use_window:
        ax2.axvspan(window_start, window_end, alpha=0.2)

    # Completion lines
    for date, qty in f2:
        ax2.axvline(date, linestyle=':', alpha=0.5)

    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    fig2.autofmt_xdate()

    st.pyplot(fig2)

# =========================
# WINDOW IMPACT SUMMARY
# =========================

if use_window:
    st.markdown("## 📈 Window Impact Summary")

    days = np.busday_count(window_start, window_end + np.timedelta64(1, 'D'))

    base_daily = np.sum(rate_per_crew) * base_crews
    window_daily = np.sum(rate_per_crew) * window_crews

    base_total = base_daily * days
    window_total = window_daily * days

    gain = window_total - base_total

    st.write(f"Business Days: {days}")
    st.write(f"Production with {base_crews} crews: {int(base_total)} total items")
    st.write(f"Production with {window_crews} crews: {int(window_total)} total items")
    st.write(f"Net Gain: +{int(gain)} items")

    # Determine completed items
    completed_items = []
    for (date, qty), task in zip(f1 + f2, tasks_span1 + tasks_span2):
        if window_start <= date <= window_end:
            completed_items.append(task)

    if completed_items:
        st.write("Items completed during window:")
        for item in completed_items:
            st.write(f"• {item}")
