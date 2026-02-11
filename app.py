import streamlit as st
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="FM Projections", layout="wide")
st.title("📊 FM Projections - Production Timeline")

st.sidebar.header("Project Parameters")

tasks = ["Stringers", "Cross Frames", "Cross Girders"]
quantities = [852, 82, 22]

rates_2_crews = np.array([16, 10, 1.5])
rate_per_crew = rates_2_crews / 2

start_date = np.datetime64("2026-02-11")
deadline_workdays = st.sidebar.slider("Deadline (workdays)", 30, 90, 57)
deadline_date = np.busday_offset(start_date, deadline_workdays)

crew_scenarios = st.sidebar.multiselect(
    "Select crew sizes to compare:",
    [2, 3, 4],
    default=[2, 3, 4]
)

total_units = sum(quantities)

def build_curve_workdays(quantities, rates, start_date):
    cumulative = [0]
    dates = [start_date]
    current_day = start_date

    for qty, rate in zip(quantities, rates):
        remaining = qty
        days_needed = int(np.ceil(qty / rate))

        for _ in range(days_needed):
            completed = min(rate, remaining)
            remaining -= completed
            cumulative.append(cumulative[-1] + completed)
            current_day = np.busday_offset(current_day, 1)
            dates.append(current_day)

    return dates, cumulative

if crew_scenarios:
    fig, axes = plt.subplots(len(crew_scenarios), 1, figsize=(14, 5*len(crew_scenarios)), sharex=True)
    
    if len(crew_scenarios) == 1:
        axes = [axes]
    
    for ax, crews in zip(axes, crew_scenarios):
        rates = rate_per_crew * crews
        dates, curve = build_curve_workdays(quantities, rates, start_date)

        durations = [int(np.ceil(q / r)) for q, r in zip(quantities, rates)]
        milestones = np.cumsum(durations)

        stringers_done = np.busday_offset(start_date, milestones[0])
        cf_done = np.busday_offset(start_date, milestones[1])
        cg_done = np.busday_offset(start_date, milestones[2])

        ax.plot(dates, curve, linewidth=2.5, label=f"{crews} Crews", color="steelblue")

        ax.axvline(deadline_date, color="red", linestyle="-", linewidth=3, label="Deadline")
        ax.text(deadline_date, total_units * 0.95,
                "DEADLINE", color="red", rotation=90,
                va="top", ha="right", fontweight="bold")

        ax.axvline(stringers_done, linestyle="--", linewidth=1, alpha=0.7)
        ax.axvline(cf_done, linestyle="--", linewidth=1, alpha=0.7)
        ax.axvline(cg_done, linestyle="--", linewidth=1, alpha=0.7)

        ax.text(stringers_done, total_units * 0.05,
                f"Stringers Done\n{stringers_done}", rotation=90, va="bottom", fontsize=9)
        ax.text(cf_done, total_units * 0.05,
                f"Cross Frames Done\n{cf_done}", rotation=90, va="bottom", fontsize=9)
        ax.text(cg_done, total_units * 0.05,
                f"Cross Girders Done\n{cg_done}", rotation=90, va="bottom", fontsize=9)

        ax.set_ylabel("Total Measurements Completed")
        ax.set_ylim(0, total_units)
        ax.set_title(f"{crews} Crews – Projected Measurement Production")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper left")

    if crew_scenarios:
        axes[-1].set_xlabel("Date")

    plt.tight_layout()
    st.pyplot(fig)
else:
    st.warning("⚠️ Please select at least one crew size to view projections.")

st.sidebar.markdown("---")
st.sidebar.subheader("📈 Task Summary")
for task, qty in zip(tasks, quantities):
    st.sidebar.metric(task, f"{qty} units")
st.sidebar.metric("Total", f"{total_units} units")
st.sidebar.metric("Start Date", str(start_date))
st.sidebar.metric("Deadline", str(deadline_date))