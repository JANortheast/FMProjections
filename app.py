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
start_date = np.datetime64(today)
if not np.is_busday(start_date):
    start_date = np.busday_offset(start_date, 0, roll="forward")

# =====================================================
# CREATE TABS
# =====================================================
tab1, tab2 = st.tabs(["Standard Projection", "Rate-Based Projection"])

# =====================================================
# -------- TAB 1: STANDARD PROJECTION ---------------
# =====================================================
with tab1:
    st.subheader("Standard Projection")

    # --- Sidebar inputs for Tab 1 ---
    st.sidebar.subheader("Tab 1: Span 7–21 Completed")
    c_s1 = st.sidebar.number_input("Stringers Completed (7–21) [Tab 1]", 0, TOTALS_SPAN1["Stringers"], 0)
    c_cf1 = st.sidebar.number_input("Cross Frames Completed (7–21) [Tab 1]", 0, TOTALS_SPAN1["Cross Frames"], 0)
    c_cg1 = st.sidebar.number_input("Cross Girders Completed (7–21) [Tab 1]", 0, TOTALS_SPAN1["Cross Girders"], 0)

    st.sidebar.subheader("Tab 1: Span 22–36B Completed")
    c_s2 = st.sidebar.number_input("Stringers Completed (22–36B) [Tab 1]", 0, TOTALS_SPAN2["Stringers"], 0)
    c_p2 = st.sidebar.number_input("Portals Completed [Tab 1]", 0, TOTALS_SPAN2["Portals"], 0)

    st.sidebar.subheader("Tab 1: Days Already Worked by 2 Crews")
    days_worked_s1 = st.sidebar.number_input("Span 7–21 Days [Tab 1]", 0, 365, 0)
    days_worked_s2 = st.sidebar.number_input("Span 22–36B Days [Tab 1]", 0, 365, 0)

    st.sidebar.subheader("Tab 1: Production Rates (per day for 2 crews)")
    stringers_rate = st.sidebar.number_input("Stringers rate [Tab 1]", 0.1, value=16.0)
    cross_frames_rate = st.sidebar.number_input("Cross Frames rate [Tab 1]", 0.1, value=10.0)
    cross_girders_rate = st.sidebar.number_input("Cross Girders rate [Tab 1]", 0.1, value=1.5)
    portals_rate = st.sidebar.number_input("Portals rate [Tab 1]", 0.1, value=2.0)

    rates_2_crews = np.array([stringers_rate, cross_frames_rate, cross_girders_rate, portals_rate])
    rate_per_crew = rates_2_crews / 2

    # --- Base crews ---
    base_crews = st.sidebar.number_input("Base Crews [Tab 1]", 1, value=2)

    # --- Deadline ---
    deadline_input = st.sidebar.date_input("Deadline [Tab 1]", dt.date(today.year, 4, 30))
    deadline_date = np.datetime64(deadline_input)

    # --- Remaining quantities adjusted for completed + days worked ---
    r_s1 = max(TOTALS_SPAN1["Stringers"] - c_s1 - stringers_rate*days_worked_s1/2, 0)
    r_cf1 = max(TOTALS_SPAN1["Cross Frames"] - c_cf1 - cross_frames_rate*days_worked_s1/2, 0)
    r_cg1 = max(TOTALS_SPAN1["Cross Girders"] - c_cg1 - cross_girders_rate*days_worked_s1/2, 0)
    r_s2 = max(TOTALS_SPAN2["Stringers"] - c_s2 - stringers_rate*days_worked_s2/2, 0)
    r_p2 = max(TOTALS_SPAN2["Portals"] - c_p2 - portals_rate*days_worked_s2/2, 0)

    # --- Scheduler ---
    def build_schedule(tasks, quantities, rates, start_date):
        remaining = quantities.copy()
        cumulative = [0]
        dates = [start_date]
        completion_dates = []
        current_day = start_date
        task_index = 0

        while task_index < len(tasks) and sum(remaining) > 0:
            if not np.is_busday(current_day):
                current_day = np.busday_offset(current_day, 0, roll="forward")
            daily_rate = rates[task_index] * base_crews
            completed = min(daily_rate, remaining[task_index])
            remaining[task_index] -= completed
            cumulative.append(cumulative[-1] + completed)
            if remaining[task_index] <= 0:
                completion_dates.append(current_day)
                task_index += 1
            current_day = np.busday_offset(current_day, 1)
            dates.append(current_day)
        return dates, cumulative, completion_dates

    # --- Span 7–21 ---
    span1_tasks = ["Stringers", "Cross Frames", "Cross Girders"]
    span1_quantities = np.array([r_s1, r_cf1, r_cg1])
    span1_dates, span1_curve, span1_completion = build_schedule(span1_tasks, span1_quantities, rate_per_crew[:3], start_date)
    span1_finish = span1_completion[-1] if span1_completion else start_date

    # --- Span 22–36B ---
    span2_tasks = ["Stringers", "Portals"]
    span2_quantities = np.array([r_s2, r_p2])
    span2_dates, span2_curve, span2_completion = build_schedule(span2_tasks, span2_quantities, np.array([rate_per_crew[0], rate_per_crew[3]]), span1_finish)
    span2_finish = span2_completion[-1] if span2_completion else span1_finish

    # --- Plotting function ---
    def plot_span(dates, curve, tasks, completion_dates, title, show_deadline):
        fig, ax = plt.subplots(figsize=(15,6))
        ax.plot(dates, curve, linewidth=3)
        colors = ["green", "orange", "purple", "blue"]
        for task, comp, color in zip(tasks, completion_dates, colors):
            ax.axvline(comp, linestyle="--", color=color)
            ax.text(comp, max(curve)*0.1, f"{task} Done\n{comp}", rotation=90, fontsize=9, color=color, fontweight="bold")
        if show_deadline:
            ax.axvline(deadline_date, color="red", linewidth=3)
        ax.set_title(title, fontweight="bold")
        ax.set_ylabel("Items Completed")
        ax.set_xlabel("Date")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        return fig

    st.subheader("Span 7–21 Remaining Projection")
    st.pyplot(plot_span(span1_dates, span1_curve, span1_tasks, span1_completion, "Span 7–21 Production", True))
    st.subheader("Span 22–36B Remaining Projection")
    st.pyplot(plot_span(span2_dates, span2_curve, span2_tasks, span2_completion, "Span 22–36B Production", False))

# =====================================================
# -------- TAB 2: RATE-BASED PROJECTION ---------------
# =====================================================
with tab2:
    st.subheader("Rate-Based Projection")

    # --- Sidebar inputs for Tab 2 ---
    st.sidebar.subheader("Tab 2: Days Measured")
    days_measured_s1 = st.sidebar.number_input("Span 7–21 Days Measured [Tab 2]", 0, 365, 1)
    days_measured_s2 = st.sidebar.number_input("Span 22–36B Days Measured [Tab 2]", 0, 365, 1)

    st.sidebar.subheader("Tab 2: Completed Quantities")
    completed_s1 = st.sidebar.number_input("Span 7–21 Total Completed Units [Tab 2]", 0, sum(TOTALS_SPAN1.values()), 0)
    completed_s2 = st.sidebar.number_input("Span 22–36B Total Completed Units [Tab 2]", 0, sum(TOTALS_SPAN2.values()), 0)

    # --- Calculate rates per day from measurements ---
    avg_rate_s1 = completed_s1 / days_measured_s1 if days_measured_s1>0 else 0.1
    avg_rate_s2 = completed_s2 / days_measured_s2 if days_measured_s2>0 else 0.1

    # --- Scheduler using rate per task proportionally ---
    def build_rate_schedule(total_qty, avg_rate, start_date):
        remaining = total_qty
        cumulative = [0]
        dates = [start_date]
        current_day = start_date
        while remaining > 0:
            if not np.is_busday(current_day):
                current_day = np.busday_offset(current_day, 0, roll="forward")
            completed = min(avg_rate, remaining)
            remaining -= completed
            cumulative.append(cumulative[-1] + completed)
            current_day = np.busday_offset(current_day, 1)
            dates.append(current_day)
        return dates, cumulative

    # --- Span 7–21 ---
    span1_total = sum(TOTALS_SPAN1.values())
    span1_dates2, span1_curve2 = build_rate_schedule(span1_total, avg_rate_s1, start_date)
    span1_finish2 = span1_dates2[-1]

    # --- Span 22–36B ---
    span2_total = sum(TOTALS_SPAN2.values())
    span2_dates2, span2_curve2 = build_rate_schedule(span2_total, avg_rate_s2, span1_finish2)
    span2_finish2 = span2_dates2[-1]

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(15,6))
    ax.plot(span1_dates2, span1_curve2, label="Span 7–21", linewidth=3)
    ax.plot(span2_dates2, span2_curve2, label="Span 22–36B", linewidth=3)
    ax.axvline(deadline_date, color="red", linewidth=3)
    ax.set_title("Rate-Based Projection", fontweight="bold")
    ax.set_ylabel("Items Completed")
    ax.set_xlabel("Date")
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    st.pyplot(fig)
