import matplotlib.pyplot as plt
import numpy as np

# =====================================================
# INPUT DATA
# =====================================================
tasks = ["Stringers", "Cross Frames", "Cross Girders"]
quantities = [852, 82, 22]

# Rates given are TOTAL for 2 crews
rates_2_crews = np.array([16, 10, 1.5])
rate_per_crew = rates_2_crews / 2

crew_scenarios = [2, 3, 4]

start_date = np.datetime64("2026-02-11")
deadline_workdays = 57
deadline_date = np.busday_offset(start_date, deadline_workdays)

total_units = sum(quantities)

# =====================================================
# FUNCTION TO BUILD PRODUCTION CURVE (WORKDAYS ONLY)
# =====================================================
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

# =====================================================
# PLOTTING
# =====================================================
fig, axes = plt.subplots(3, 1, figsize=(15, 14), sharex=True)

for ax, crews in zip(axes, crew_scenarios):
    rates = rate_per_crew * crews
    dates, curve = build_curve_workdays(quantities, rates, start_date)

    # Task durations (workdays)
    durations = [int(np.ceil(q / r)) for q, r in zip(quantities, rates)]
    milestones = np.cumsum(durations)

    stringers_done = np.busday_offset(start_date, milestones[0])
    cf_done = np.busday_offset(start_date, milestones[1])
    cg_done = np.busday_offset(start_date, milestones[2])

    # Production curve
    ax.plot(dates, curve, linewidth=2, label=f"{crews} Crews")

    # SOLID RED DEADLINE
    ax.axvline(deadline_date, color="red", linestyle="-", linewidth=3, label="Deadline")
    ax.text(deadline_date, total_units * 0.95,
            "DEADLINE", color="red", rotation=90,
            va="top", ha="right", fontweight="bold")

    # Milestone lines
    ax.axvline(stringers_done, linestyle="--", linewidth=1)
    ax.axvline(cf_done, linestyle="--", linewidth=1)
    ax.axvline(cg_done, linestyle="--", linewidth=1)

    ax.text(stringers_done, total_units * 0.05,
            f"Stringers Done\n{stringers_done}", rotation=90, va="bottom")
    ax.text(cf_done, total_units * 0.05,
            f"Cross Frames Done\n{cf_done}", rotation=90, va="bottom")
    ax.text(cg_done, total_units * 0.05,
            f"Cross Girders Done\n{cg_done}", rotation=90, va="bottom")

    # Formatting
    ax.set_ylabel("Total Measurements Completed")
    ax.set_ylim(0, total_units)
    ax.set_title(f"{crews} Crews – Projected Measurement Production")
    ax.grid(True)
    ax.legend()

axes[-1].set_xlabel("Date")

plt.tight_layout()
plt.show()