import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, date
import calendar

st.set_page_config(layout="wide")

st.title("FM Projections Dashboard")

# =====================================================
# SETTINGS
# =====================================================

# Automatically use today's date
today = np.datetime64(date.today())

# If today is weekend, move to next business day
if not np.is_busday(today):
    today = np.busday_offset(today, 0, roll='forward')

start_date = today

# Deadline (manually change year/month here)
DEADLINE_YEAR = 2026
DEADLINE_MONTH = 4   # April

last_day = calendar.monthrange(DEADLINE_YEAR, DEADLINE_MONTH)[1]
deadline_date = np.datetime64(date(DEADLINE_YEAR, DEADLINE_MONTH, last_day))

# =====================================================
# DATA (EDIT THESE VALUES)
# =====================================================

span1_tasks = ["Temp Stringers", "Permanent Stringers"]
span1_quantities = np.array([120, 180])
span1_rates = np.array([8, 6])  # units per crew per day

# =====================================================
# CREW LOGIC
# =====================================================

def get_crews(current_day):
    """
    Example crew schedule logic.
    Modify as needed.
    """
    # Example: 2 crews after March 15
    if current_day >= np.datetime64("2026-03-15"):
        return 2
    return 1


# =====================================================
# BUSINESS-DAY SAFE SCHEDULER
# =====================================================

def build_schedule(quantities, rates, start):

    # Ensure start date is business day
    if not np.is_busday(start):
        start = np.busday_offset(start, 0, roll='forward')

    remaining = quantities.copy()
    cumulative = [0]
    dates = [start]

    current_day = start
    task_index = 0
    completion_dates = []

    while task_index < len(remaining):

        # Skip weekends
        if not np.is_busday(current_day):
            current_day = np.busday_offset(current_day, 0, roll='forward')

        crews_today = get_crews(current_day)
        daily_rate = rates[task_index] * crews_today

        completed = min(daily_rate, remaining[task_index])
        remaining[task_index] -= completed

        cumulative.append(cumulative[-1] + completed)

        if remaining[task_index] <= 0:
            # Ensure completion date is weekday
            if not np.is_busday(current_day):
                current_day = np.busday_offset(current_day, 0, roll='forward')

            completion_dates.append(current_day)
            task_index += 1

        # Move to next business day
        current_day = np.busday_offset(current_day, 1)
        dates.append(current_day)

    return dates, cumulative, completion_dates


# =====================================================
# BUILD SCHEDULE
# =====================================================

span1_dates, span1_curve, span1_completion = build_schedule(
    span1_quantities,
    span1_rates,
    start_date
)

final_completion = span1_completion[-1]

# =====================================================
# SCHEDULE STATUS (Ahead or Behind)
# =====================================================

days_difference = np.busday_count(deadline_date, final_completion)

if final_completion > deadline_date:
    status_text = f"🔴 {abs(days_difference)} business days BEHIND schedule"
else:
    status_text = f"🟢 {abs(days_difference)} business days AHEAD of schedule"

st.subheader(status_text)

# =====================================================
# PLOT
# =====================================================

fig, ax = plt.subplots(figsize=(14,7))

# Main progress curve
ax.plot(span1_dates, span1_curve, linewidth=3)

# Solid red deadline line
ax.axvline(deadline_date, color="red", linewidth=3)
ax.text(deadline_date,
        max(span1_curve)*0.9,
        "DEADLINE",
        rotation=90,
        color="red",
        fontweight="bold",
        verticalalignment="top")

# Dotted lines for task completions
for task, comp_date in zip(span1_tasks, span1_completion):
    ax.axvline(comp_date, linestyle="--", alpha=0.7)
    ax.text(comp_date,
            max(span1_curve)*0.05,
            f"{task} Complete\n{comp_date}",
            rotation=90,
            verticalalignment="bottom")

# Start marker
ax.scatter(span1_dates[0], span1_curve[0], s=120)
ax.text(span1_dates[0],
        span1_curve[0],
        f" Start\n{span1_dates[0]}",
        verticalalignment="bottom")

# Finish marker
ax.scatter(final_completion, span1_curve[-1], s=120)
ax.text(final_completion,
        span1_curve[-1],
        f" Finish\n{final_completion}",
        verticalalignment="bottom")

ax.set_title("Span 7–21 Projection")
ax.set_ylabel("Cumulative Quantity")
ax.set_xlabel("Date")
ax.grid(True)

st.pyplot(fig)
