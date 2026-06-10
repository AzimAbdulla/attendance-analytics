"""
MONTHLY ATTENDANCE PERFORMANCE REPORT
-------------------------------------
This report is the high-level 'Executive Scorecard'. It evaluates employee behavior
over a month and assigns a numeric score based on presence, punctuality, and work hours.

It uses a deductive model: employees start with a base score, and points are 
removed for absences, late arrivals, or short work hours.
"""

import frappe
from frappe import _
from frappe.utils import getdate, add_days, get_datetime, now_datetime, add_months
import datetime
from itertools import groupby

def execute(filters=None):
    """
    Main entry point.
    - Loads dynamic scoring rules from the Settings document.
    - Calculates scores for Current and Previous months to show trends.
    - Returns data rows and the Top 10 performance bar chart.
    """
    if not filters:
        filters = {}

    settings = get_settings()
    columns = get_columns()
    data = get_data(filters, settings)
    chart = get_chart(data)
    
    return columns, data, None, chart

def get_settings():
    """
    Retrieves the global configuration from 'Attendance Performance Settings'.
    Ensures penalties and office timings are dynamic and not hardcoded in Python.
    """
    settings = frappe.get_doc("Attendance Performance Settings")
    
    # office_start_time (time): Standard shift start time (e.g., 09:00:00).
    if isinstance(settings.office_start_time, str):
        settings.office_start_time = datetime.datetime.strptime(settings.office_start_time, "%H:%M:%S").time()
    elif isinstance(settings.office_start_time, datetime.timedelta):
        settings.office_start_time = (datetime.datetime.min + settings.office_start_time).time()

    # severe_late_threshold (time): Punctuality cutoff for major point deductions.
    if isinstance(settings.severe_late_threshold, str):
        settings.severe_late_threshold = datetime.datetime.strptime(settings.severe_late_threshold, "%H:%M:%S").time()
    elif isinstance(settings.severe_late_threshold, datetime.timedelta):
        settings.severe_late_threshold = (datetime.datetime.min + settings.severe_late_threshold).time()

    return settings

def get_chart(data):
    """Generates the 'Top 10 Employees' bar chart displayed at the top of the report."""
    if not data:
        return None

    # top_10 (list): Sliced from the final sorted data list.
    top_10 = data[:10]
    
    chart = {
        "data": {
            "labels": [d["employee_name"] for d in top_10],
            "datasets": [
                {
                    "name": _("Final Score"),
                    "values": [d["final_score"] for d in top_10]
                }
            ]
        },
        "type": "bar",
        "colors": ["#3498db"],
        "axisOptions": {
            "xIsSeries": 1
        }
    }
    
    return chart

def get_columns():
    """Defines the 20 columns for the employee performance ranking table."""
    return [
        {"label": _("Rank"), "fieldname": "rank", "fieldtype": "Int", "width": 60},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
        {"label": _("Total Working Days"), "fieldname": "total_working_days", "fieldtype": "Int", "width": 130},
        {"label": _("Present"), "fieldname": "present_days", "fieldtype": "Int", "width": 100},
        {"label": _("Half Days"), "fieldname": "half_days", "fieldtype": "Int", "width": 90},
        {"label": _("Leave"), "fieldname": "leave_days", "fieldtype": "Int", "width": 90},
        {"label": _("WFH"), "fieldname": "wfh_days", "fieldtype": "Int", "width": 90},
        {"label": _("Absent"), "fieldname": "absent_days", "fieldtype": "Int", "width": 100},
        {"label": _("Attendance %"), "fieldname": "attendance_percentage", "fieldtype": "Percent", "width": 110},
        {"label": _("Total Hours"), "fieldname": "expected_hours", "fieldtype": "Data", "width": 120},
        {"label": _("Exp. (Present)"), "fieldname": "expected_present_hours", "fieldtype": "Data", "width": 120},
        {"label": _("Actual Hours"), "fieldname": "actual_hours", "fieldtype": "Data", "width": 120},
        {"label": _("Compliance %"), "fieldname": "compliance_percentage", "fieldtype": "Percent", "width": 110},
        {"label": _("Overall Work Hour %"), "fieldname": "overall_compliance_percentage", "fieldtype": "Percent", "width": 130},
        {"label": _("Late Arrival"), "fieldname": "late_arrival_count", "fieldtype": "Int", "width": 130},
        {"label": _("Severe Late"), "fieldname": "severe_late_count", "fieldtype": "Int", "width": 140},
        {"label": _("Score"), "fieldname": "final_score", "fieldtype": "Float", "width": 110},
        {"label": _("Trend (Score)"), "fieldname": "trend", "fieldtype": "Data", "width": 110},
        {"label": _("Trend (Rank)"), "fieldname": "rank_trend", "fieldtype": "Data", "width": 110},
    ]

def get_data(filters, settings):
    """Orchestrates data fetching and resolving rankings and trends."""
    month = filters.get("month")
    year = filters.get("year")
    if not month or not year: return []

    # --- Setup Evaluation Periods ---
    curr_start = getdate(f"{year}-{month}-01")
    curr_end = add_days(add_months(curr_start, 1), -1)
    
    # Prorate end date to today if evaluating the current ongoing month.
    today = getdate(now_datetime())
    if curr_end > today: curr_end = today

    # standard_working_days (int): Contractual days expected minus company holidays.
    standard_working_days = get_standard_working_days(curr_start, curr_end)

    # Setup dates for historical month to enable Green/Red trend arrows.
    prev_start = add_months(curr_start, -1)
    prev_end = add_days(curr_start, -1)
    prev_standard_working_days = get_standard_working_days(prev_start, prev_end)

    employees = get_employees(filters)
    employee_list = [e.name for e in employees]
    if not employee_list: return []

    # calculate result dictionaries for current and previous periods.
    curr_results = calculate_scores_and_ranks(employee_list, curr_start, curr_end, settings, employees, standard_working_days)
    prev_results = calculate_scores_and_ranks(employee_list, prev_start, prev_end, settings, employees, prev_standard_working_days)

    report_data = []
    for emp_id in curr_results:
        data = curr_results[emp_id]
        
        # --- SCORE TREND ---
        trend = '<span style="color:grey">—</span>'
        if emp_id in prev_results:
            diff = data["final_score"] - prev_results[emp_id]["final_score"]
            if diff > 0.1:
                trend = f'<span style="color:green">↑ +{round(diff, 1)}</span>'
            elif diff < -0.1:
                trend = f'<span style="color:red">↓ {round(diff, 1)}</span>'
        data["trend"] = trend

        # --- RANK TREND ---
        rank_trend = '<span style="color:grey">—</span>'
        if emp_id in prev_results:
            curr_rank = data["rank"]
            prev_rank = prev_results[emp_id]["rank"]
            
            if curr_rank < prev_rank: # Rank improved (e.g. from 5th to 2nd)
                rank_trend = f'<span style="color:green">↑ {prev_rank - curr_rank}</span>'
            elif curr_rank > prev_rank: # Rank dropped
                rank_trend = f'<span style="color:red">↓ {curr_rank - prev_rank}</span>'
        
        data["rank_trend"] = rank_trend
        report_data.append(data)

    # Sort final output strictly by numeric rank.
    report_data.sort(key=lambda x: x["rank"])
    return report_data

def calculate_scores_and_ranks(employee_list, start_date, end_date, settings, employees_meta, standard_working_days):
    """
    Main mathematical logic for performance scoring.
    Iterates through each employee, calculates work hours via Greedy logic, 
    and applies all penalty modifiers.
    """
    # Bulk fetch attendance documents
    attendance_records = frappe.get_all(
        "Attendance",
        filters={"employee": ["in", employee_list], "attendance_date": ["between", [start_date, end_date]], "docstatus": 1},
        fields=["employee", "attendance_date", "status", "leave_type"]
    )
    att_map = {}
    for att in attendance_records:
        att_map.setdefault(att.employee, []).append(att)

    # Bulk fetch raw biometric punches
    checkin_records = frappe.get_all(
        "Employee Checkin",
        filters={"employee": ["in", employee_list], "time": ["between", [get_datetime(f"{start_date} 00:00:00"), get_datetime(f"{end_date} 23:59:59")]], "skip_auto_attendance": 0},
        fields=["employee", "time", "log_type"],
        order_by="time asc"
    )
    checkin_map = {}
    for checkin in checkin_records:
        date_str = str(checkin.time.date())
        checkin_map.setdefault(checkin.employee, {}).setdefault(date_str, []).append(checkin)

    # leave_penalties (dict): Pre-mapped deductions for specific leave types from settings.
    leave_penalties = {
        "Privilege Leave": settings.privilege_leave_penalty,
        "Sick Leave": settings.sick_leave_penalty,
        "Casual Leave": settings.casual_leave_penalty,
        "Maternity Leave": settings.maternity_leave_penalty,
        "Compensatory Off": settings.comp_off_penalty,
        "Holiday Duty": settings.holiday_duty_penalty,
        "Leave Without Pay": settings.lwp_penalty
    }

    excluded_branches = [b.branch for b in settings.excluded_branches]
    excluded_employment_types = [t.employment_type for t in settings.excluded_employment_types]
    id_pattern = (settings.excluded_id_pattern or "").upper()

    scores_list = []

    for emp in employees_meta:
        # EXCLUSION LOGIC: Skip employees matching exclusion rules (e.g. Interns or remote branches).
        if settings.enable_wfh_exclusion:
            is_excluded = False
            if id_pattern and id_pattern in str(emp.employee_number or "").upper(): is_excluded = True
            if not is_excluded and emp.branch in excluded_branches: is_excluded = True
            if not is_excluded and emp.employment_type in excluded_employment_types: is_excluded = True
            if is_excluded: continue

        emp_att = att_map.get(emp.name, [])
        emp_checkins = checkin_map.get(emp.name, {})

        # stats (dict): Local month accumulator for counts and physical work time.
        stats = {
            "present_days": 0, "half_days": 0, "leave_days": 0, "wfh_days": 0,
            "absent_days": 0, "lwp_days": 0, "total_working_days": len(emp_att),
            "late_arrival_count": 0, "severe_late_count": 0,
            "actual_work_seconds": 0 # Sum of physical presence accumulated via Greedy logic.
        }
        
        # Initial grade starts at Base Score. Modifiers are added/subtracted.
        score = settings.base_score
        
        for att in emp_att:
            status = att.status
            date_str = str(att.attendance_date)
            
            # --- STATUS-BASED POINT DEDUCTIONS ---
            if status == "Present": stats["present_days"] += 1
            elif status == "Half Day":
                stats["half_days"] += 1
                score -= settings.half_day_penalty
            elif "Leave" in status:
                stats["leave_days"] += 1
                if att.leave_type == "Leave Without Pay": stats["lwp_days"] += 1
                score -= leave_penalties.get(att.leave_type, settings.default_leave_penalty)
            elif "Work From Home" in status or "WFH" in status:
                stats["wfh_days"] += 1
                score -= settings.wfh_status_penalty
            elif status == "Absent":
                stats["absent_days"] += 1
                score -= settings.absent_penalty
                
            # --- PUNCTUALITY & WORK HOUR AUDIT ---
            if date_str in emp_checkins:
                day_logs = emp_checkins[date_str]
                checkin_time = day_logs[0].time.time()
                
                # 1. First-In Log Punctuality Check
                if checkin_time >= settings.office_start_time:
                    diff = datetime.datetime.combine(datetime.date.min, checkin_time) - \
                           datetime.datetime.combine(datetime.date.min, settings.office_start_time)
                    if (diff.total_seconds() / 60) > settings.late_grace_period:
                        stats["late_arrival_count"] += 1
                        if checkin_time <= settings.severe_late_threshold: score -= settings.standard_late_penalty
                        else:
                            score -= settings.severe_late_penalty
                            stats["severe_late_count"] += 1

                # 2. Clustered Greedy Work-Hour Accumulation
                day_work_seconds = 0
                day_clusters = []
                for log_type, group in groupby(day_logs, key=lambda x: x.log_type):
                    day_clusters.append((log_type, list(group)))
                for i in range(len(day_clusters) - 1):
                    if day_clusters[i][0] == "IN" and day_clusters[i+1][0] == "OUT":
                        day_work_seconds += (day_clusters[i+1][1][-1].time - day_clusters[i][1][0].time).total_seconds()

                stats["actual_work_seconds"] += day_work_seconds

                # Apply scoring mods for exceeding shift targets or excessive breaks
                if settings.enable_duration_scoring:
                    if day_work_seconds >= (settings.work_target_hours * 3600): score += settings.work_bonus
                    if len(day_logs) >= 2:
                        span = (day_logs[-1].time - day_logs[0].time).total_seconds()
                        if (max(span - day_work_seconds, 0)) > (settings.break_threshold_hours * 3600):
                            score -= settings.break_penalty

        # --- HABITUAL PUNCTUALITY PENALTY ---
        if settings.enable_habitual_penalties:
            if stats["severe_late_count"] > settings.habitual_threshold_2: score -= settings.habitual_penalty_2
            elif stats["severe_late_count"] > settings.habitual_threshold_1: score -= settings.habitual_penalty_1

        # --- REWARDS FOR PERFECT LOGS ---
        if settings.enable_rewards and stats["total_working_days"] > 0:
            if stats["late_arrival_count"] == 0: score += settings.punctuality_bonus
            if stats["absent_days"] == 0 and stats["half_days"] == 0 and stats["lwp_days"] == 0: score += settings.consistency_bonus

        # --- KPI RESOLUTION ---
        # attendance_percentage (float): Presence rate compared to total working days.
        attendance_percentage = 0
        if standard_working_days > 0:
            attendance_percentage = (stats["present_days"] + stats["wfh_days"] + (stats["half_days"] * 0.5)) / standard_working_days * 100

        # Hours Compliance: Actual worked seconds / Expected 8h per present day.
        expected_present_seconds = stats["present_days"] * 8 * 3600
        compliance_percentage = 0
        if expected_present_seconds > 0:
            compliance_percentage = (stats["actual_work_seconds"] / expected_present_seconds) * 100

        # Overall Compliance: Actual worked seconds / Total contractual month target.
        expected_work_seconds = standard_working_days * 8 * 3600
        overall_compliance_percentage = 0
        if expected_work_seconds > 0:
            overall_compliance_percentage = (stats["actual_work_seconds"] / expected_work_seconds) * 100

        # --- DYNAMIC COMPLIANCE SCORING MODIFIERS ---
        if getattr(settings, "enable_compliance_scoring", 0) and stats["present_days"] > 0:
            if compliance_percentage >= getattr(settings, "compliance_threshold_1", 90.0):
                score += getattr(settings, "compliance_modifier_1", 2.0)
            elif compliance_percentage >= getattr(settings, "compliance_threshold_2", 80.0):
                score += getattr(settings, "compliance_modifier_2", 1.0)
            elif compliance_percentage >= getattr(settings, "compliance_threshold_3", 70.0):
                score += getattr(settings, "compliance_modifier_3", 0.0)
            elif compliance_percentage >= getattr(settings, "compliance_threshold_4", 60.0):
                score += getattr(settings, "compliance_modifier_4", -1.0)
            else:
                score += getattr(settings, "compliance_modifier_5", -3.0)

        # Floor score at 0.0
        score = max(score, 0)

        scores_list.append({
            "employee": emp.name,
            "employee_id": str(emp.name).split(":")[0].strip(),
            "employee_name": emp.employee_name,
            "department": emp.department,
            "total_working_days": standard_working_days,
            "present_days": stats["present_days"],
            "half_days": stats["half_days"],
            "leave_days": stats["leave_days"],
            "wfh_days": stats["wfh_days"],
            "absent_days": stats["absent_days"],
            "attendance_percentage": attendance_percentage,
            "expected_hours": format_duration_short(expected_work_seconds),
            "expected_present_hours": format_duration_short(expected_present_seconds),
            "actual_hours": format_duration_short(stats["actual_work_seconds"]),
            "compliance_percentage": compliance_percentage,
            "overall_compliance_percentage": overall_compliance_percentage,
            "late_arrival_count": stats["late_arrival_count"],
            "severe_late_count": stats["severe_late_count"],
            "final_score": score,
        })

    # Sort final list by score (Descending) to assign ranks.
    scores_list.sort(key=lambda x: x["final_score"], reverse=True)
    
    results_map = {}
    for i, item in enumerate(scores_list):
        item["rank"] = i + 1
        results_map[item["employee"]] = item

    return results_map

def format_duration_short(seconds):
    """Formats raw time seconds into the standard 'Xh YYm' display string."""
    if seconds <= 0: return "0h 00m"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m:02d}m"

def get_standard_working_days(start_date, end_date):
    """
    Calculates expected work days based on the '2026' Holiday List.
    Accounts for Sundays as Weekly Offs.
    """
    holidays = frappe.get_all('Holiday', 
        filters={'parent': '2026', 'holiday_date': ['between', [start_date, end_date]]}, 
        fields=['holiday_date', 'weekly_off']
    )
    holiday_dates = {h.holiday_date for h in holidays}
    working_days = 0
    curr_date = getdate(start_date)
    while curr_date <= getdate(end_date):
        # Skip Sunday (weekday 6) or specific Holiday.
        if curr_date not in holiday_dates and curr_date.weekday() != 6:
            working_days += 1
        curr_date = add_days(curr_date, 1)
    return working_days

def get_employees(filters):
    """Fetches list of active employees matching company/dept filters."""
    conditions = {"status": "Active"}
    if filters.get("department"): conditions["department"] = filters.get("department")
    if filters.get("branch"): conditions["branch"] = filters.get("branch")
    if filters.get("employee"): conditions["name"] = filters.get("employee")
        
    return frappe.get_all(
        "Employee",
        filters=conditions,
        fields=["name", "employee_name", "department", "employee_number", "branch", "employment_type"]
    )

# ==============================================================================
# WARNINGS & CRITICAL DEPENDENCIES
# ==============================================================================
# 1. YEAR HARDCODE: 'get_standard_working_days' uses '2026' as the parent
#    Holiday List name. Ensure this is updated to '2027' next year.
#
# 2. SETTINGS DEPENDENCY: Every scoring modifier depends on the fields in 
#    the 'Attendance Performance Settings' document. Renaming fields in that
#    DocType will cause this report to crash.
#
# 3. SCORING THRESHOLDS: Modifiers are fetched via 'getattr'. To add levels, 
#    update both the JSON metadata and the logic block in this file.
# ==============================================================================
