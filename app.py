import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

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
    "Stringers": 852,
    "Cross Frames": 82,
    "Cross Girders": 22,
    "Portals": 12
}

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def next_business_day(date):
    date += timedelta(days=1)
    while date.weekday() >= 5:
        date += timedelta(days=1)
    return date


def build_schedule(totals, rates, start_date):
    remaining = totals.copy()
    current_date = start_date

    schedule = {k: [(current_date, 0)] for k in totals}
    completion_dates = {}

    while any(v > 0 for v in remaining.values()):
        for item in remaining:
            if remaining[item] > 0:
                remaining[item] -= rates.get(item, 0)
                produced = totals[item] - max(remaining[item], 0)
                schedule[item].append((current_date, min(produced, totals[item])))

                if remaining[item] <= 0 and item not in completion_dates:
                    completion_dates[item] = current_date

        current_date = next_business_day(current_date)

    return schedule, completion_dates


def plot_schedule(schedule, totals, title, deadline=None):
    fig, ax = plt.subplots(figsize=(10, 5))

    for item, data in schedule.items():
        x = [d[0] for d in data]
        y = [d[1] for d in data]
        ax.plot(x, y, label=item)
        ax.axhline(totals[item], linestyle="--", linewidth=0.8)

    if deadline:
        ax.axvline(deadline, linestyle="-", linewidth=2)

    ax.set_title(title)
    ax.set_ylabel("Cumulative Quantity")
    ax.set_xlabel("Date")
    ax.legend()
    ax.set_ylim(bottom=0)
    ax.grid(True)

    return fig


# =====================================================
# SIDEBAR INPUTS
# =====================================================

st.sidebar.header("⚙️ Inputs")

span1_start = st.sidebar.date_input("Span 7–21 Start Date", datetime.today())
deadline = st.sidebar.date_input("Span 7–21 Deadline")

span1_rates = {}
st.sidebar.markdown("### Span 7–21 Rates (Per Day)")
for item in TOTALS_SPAN1:
    span1_rates[item] = st.sidebar.number_input(
        f"{item} Rate",
        min_value=0.0,
        value=5.0,
        step=0.5
    )

span2_rates = {}
st.sidebar.markdown("### Span 22–36B Rates (Per Day)")
for item in TOTALS_SPAN2:
    span2_rates[item] = st.sidebar.number_input(
        f"{item} Rate ",
        min_value=0.0,
        value=5.0,
        step=0.5,
        key=f"span2_{item}"
    )

# =====================================================
# ITEM SELECTION
# =====================================================

st.sidebar.markdown("### 📌 Span 7–21 Display Items")

if st.sidebar.button("Select All Span 7–21"):
    selected_span1_items = list(TOTALS_SPAN1.keys())
elif st.sidebar.button("Clear All Span 7–21"):
    selected_span1_items = []
else:
    selected_span1_items = st.sidebar.multiselect(
        "Select items to display (Span 7–21)",
        list(TOTALS_SPAN1.keys()),
        default=list(TOTALS_SPAN1.keys())
    )

st.sidebar.markdown("### 📌 Span 22–36B Display Items")

if st.sidebar.button("Select All Span 22–36B"):
    selected_span2_items = list(TOTALS_SPAN2.keys())
elif st.sidebar.button("Clear All Span 22–36B"):
    selected_span2_items = []
else:
    selected_span2_items = st.sidebar.multiselect(
        "Select items to display (Span 22–36B)",
        list(TOTALS_SPAN2.keys()),
        default=list(TOTALS_SPAN2.keys())
    )

filter_completion = st.sidebar.checkbox(
    "Completion based only on selected items",
    value=True
)

# =====================================================
# BUILD SCHEDULES
# =====================================================

if selected_span1_items:
    filtered_span1_totals = {k: v for k, v in TOTALS_SPAN1.items() if k in selected_span1_items}
    filtered_span1_rates = {k: span1_rates[k] for k in selected_span1_items}

    span1_schedule, span1_completion = build_schedule(
        filtered_span1_totals,
        filtered_span1_rates,
        span1_start
    )

    if filter_completion:
        span1_finish = max(span1_completion.values())
    else:
        full_schedule, full_completion = build_schedule(TOTALS_SPAN1, span1_rates, span1_start)
        span1_finish = max(full_completion.values())

else:
    span1_schedule = {}
    span1_finish = span1_start
    st.warning("No items selected for Span 7–21")

# Span 2 starts after Span 1 finish
span2_start = next_business_day(span1_finish)

if selected_span2_items:
    filtered_span2_totals = {k: v for k, v in TOTALS_SPAN2.items() if k in selected_span2_items}
    filtered_span2_rates = {k: span2_rates[k] for k in selected_span2_items}

    span2_schedule, span2_completion = build_schedule(
        filtered_span2_totals,
        filtered_span2_rates,
        span2_start
    )
else:
    span2_schedule = {}
    st.warning("No items selected for Span 22–36B")

# =====================================================
# DISPLAY OUTPUT
# =====================================================

col1, col2 = st.columns(2)

with col1:
    if span1_schedule:
        fig1 = plot_schedule(
            span1_schedule,
            filtered_span1_totals,
            "Span 7–21 Production",
            deadline=deadline
        )
        st.pyplot(fig1)

with col2:
    if span2_schedule:
        fig2 = plot_schedule(
            span2_schedule,
            filtered_span2_totals,
            "Span 22–36B Production"
        )
        st.pyplot(fig2)

# =====================================================
# COMPLETION METRICS
# =====================================================

st.markdown("### 📅 Completion Dates")

if selected_span1_items:
    st.write(f"Span 7–21 Finish: **{span1_finish.date()}**")

if selected_span2_items and span2_schedule:
    span2_finish = max([d[-1][0] for d in span2_schedule.values()])
    st.write(f"Span 22–36B Finish: **{span2_finish.date()}**")
