# =====================================================
# SPAN BREAKDOWN
# =====================================================

# Span 7–21 quantities
span1_tasks = ["Stringers", "Cross Frames", "Cross Girders"]
span1_quantities = np.array([
    stringers,
    cross_frames,
    cross_girders
], dtype=float)

span1_rates = rate_per_crew[:3]

# Span 22–36B quantities
additional_stringers_span2 = 1369  # fixed value per your instruction

span2_tasks = ["Stringers", "Portals"]
span2_quantities = np.array([
    additional_stringers_span2,
    portals
], dtype=float)

span2_rates = np.array([
    rate_per_crew[0],   # stringers rate per crew
    rate_per_crew[3]    # portals rate per crew
])

# =====================================================
# SCHEDULE FUNCTION (Reusable)
# =====================================================

def build_span_schedule(quantities, rates, base_crews, windows, start_date):

    if sum(quantities) == 0:
        return [start_date], [0], [start_date]

    remaining = quantities.copy()
    cumulative = [0]
    dates = [start_date]

    current_day = start_date
    task_index = 0
    task_completion_dates = []

    while task_index < len(remaining):

        crews_today = get_crews_for_day(current_day, base_crews, windows)
        daily_rate = rates[task_index] * crews_today

        completed = min(daily_rate, remaining[task_index])
        remaining[task_index] -= completed

        cumulative.append(cumulative[-1] + completed)

        if remaining[task_index] <= 0:
            task_completion_dates.append(current_day)
            task_index += 1

        current_day = np.busday_offset(current_day, 1)
        dates.append(current_day)

    return dates, cumulative, task_completion_dates


# =====================================================
# RUN SPAN 7–21
# =====================================================

span1_dates, span1_curve, span1_completion_dates = build_span_schedule(
    span1_quantities,
    span1_rates,
    base_crews,
    crew_windows,
    start_date
)

span1_finish = span1_completion_dates[-1]

# =====================================================
# RUN SPAN 22–36B (Starts After Span 1)
# =====================================================

span2_start = np.busday_offset(span1_finish, 1)

span2_dates, span2_curve, span2_completion_dates = build_span_schedule(
    span2_quantities,
    span2_rates,
    base_crews,
    crew_windows,
    span2_start
)

span2_finish = span2_completion_dates[-1]

# =====================================================
# PLOT SPAN 7–21
# =====================================================

fig1, ax1 = plt.subplots(figsize=(12, 6))

ax1.plot(span1_dates, span1_curve, linewidth=3)
ax1.set_title("Span 7–21 Production Timeline", fontweight="bold")
ax1.set_ylabel("Items Completed (each)")
ax1.set_xlabel("Date")
ax1.grid(True, alpha=0.3)

for task, comp_date in zip(span1_tasks, span1_completion_dates):
    ax1.axvline(comp_date, linestyle="--", alpha=0.7)
    ax1.text(comp_date, max(span1_curve)*0.05,
             f"{task}\n{comp_date}",
             rotation=90,
             fontsize=9,
             fontweight="bold")

plt.tight_layout()
st.pyplot(fig1)

# =====================================================
# PLOT SPAN 22–36B
# =====================================================

fig2, ax2 = plt.subplots(figsize=(12, 6))

ax2.plot(span2_dates, span2_curve, linewidth=3)
ax2.set_title("Span 22–36B Production Timeline", fontweight="bold")
ax2.set_ylabel("Items Completed (each)")
ax2.set_xlabel("Date")
ax2.grid(True, alpha=0.3)

for task, comp_date in zip(span2_tasks, span2_completion_dates):
    ax2.axvline(comp_date, linestyle="--", alpha=0.7)
    ax2.text(comp_date, max(span2_curve)*0.05,
             f"{task}\n{comp_date}",
             rotation=90,
             fontsize=9,
             fontweight="bold")

plt.tight_layout()
st.pyplot(fig2)

# =====================================================
# SUMMARY OUTPUT
# =====================================================

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Span Completion Dates")

st.sidebar.write(f"Span 7–21 Finish: {span1_finish}")
st.sidebar.write(f"Span 22–36B Finish: {span2_finish}")
