import frappe
from frappe import _
from frappe.utils import getdate, add_days, get_datetime, now_datetime, add_months
import datetime
from itertools import groupby

def execute(filters=None):
    if not filters:
        filters = {}

    settings = get_settings()
    columns = get_columns()
    data = get_data(filters, settings)
    chart = get_chart(data)
    
    return columns, data, None, chart

def get_settings():
    settings = frappe.get_doc("Attendance Performance Settings")
    
    # Convert time strings to objects
    if isinstance(settings.office_start_time, str):
        settings.office_start_time = datetime.datetime.strptime(settings.office_start_time, "%H:%M:%S").time()
    elif isinstance(settings.office_start_time, datetime.timedelta):
        settings.office_start_time = (datetime.datetime.min + settings.office_start_time).time()

    if isinstance(settings.severe_late_threshold, str):
        settings.severe_late_threshold = datetime.datetime.strptime(settings.severe_late_threshold, "%H:%M:%S").time()
    elif isinstance(settings.severe_late_threshold, datetime.timedelta):
        settings.severe_late_threshold = (datetime.datetime.min + settings.severe_late_threshold).time()

    return settings

def get_chart(data):
    if not data:
        return None

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
        "colors": ["#7cd6fd"]
    }
    
    return chart

def get_columns():
    return [
        {"label": _("Rank"), "fieldname": "rank", "fieldtype": "Int", "width": 60},
        {"label": _("ID"), "fieldname": "employee_id", "fieldtype": "Data", "width": 100},
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
        {"label": _("Late Arrival"), "fieldname": "late_arrival_count", "fieldtype": "Int", "width": 130},
        {"label": _("Severe Late"), "fieldname": "severe_late_count", "fieldtype": "Int", "width": 140},
        {"label": _("Score"), "fieldname": "final_score", "fieldtype": "Float", "width": 110},
        {"label": _("Trend (Score)"), "fieldname": "trend", "fieldtype": "Data", "width": 110},
        {"label": _("Trend (Rank)"), "fieldname": "rank_trend", "fieldtype": "Data", "width": 110},
    ]

def get_data(filters, settings):
    month = filters.get("month")
    year = filters.get("year")
    if not month or not year: return []

    # Current Period
    curr_start = getdate(f"{year}-{month}-01")
    curr_end = add_days(add_months(curr_start, 1), -1)
    today = getdate(now_datetime())
    if curr_end > today: curr_end = today

    # Standard Working Days for the month (based on Holiday List '2026' and Sundays)
    standard_working_days = get_standard_working_days(curr_start, curr_end)

    # Previous Period
    prev_start = add_months(curr_start, -1)
    prev_end = add_days(curr_start, -1)
    prev_standard_working_days = get_standard_working_days(prev_start, prev_end)

    employees = get_employees(filters)
    employee_list = [e.name for e in employees]
    if not employee_list: return []

    # Calculate Current Scores and Ranks
    curr_results = calculate_scores_and_ranks(employee_list, curr_start, curr_end, settings, employees, standard_working_days)
    
    # Calculate Previous Scores and Ranks
    prev_results = calculate_scores_and_ranks(employee_list, prev_start, prev_end, settings, employees, prev_standard_working_days)

    report_data = []
    for emp_id in curr_results:
        data = curr_results[emp_id]
        
        # 1. Score Trend
        trend = '<span style="color:grey">—</span>'
        if emp_id in prev_results:
            diff = data["final_score"] - prev_results[emp_id]["final_score"]
            if diff > 0.1:
                trend = f'<span style="color:green">↑ +{round(diff, 1)}</span>'
            elif diff < -0.1:
                trend = f'<span style="color:red">↓ {round(diff, 1)}</span>'

        data["trend"] = trend

        # 2. Rank Trend (Climbed/Fallen number)
        rank_trend = '<span style="color:grey">—</span>'
        if emp_id in prev_results:
            curr_rank = data["rank"]
            prev_rank = prev_results[emp_id]["rank"]
            
            if curr_rank < prev_rank: # Improved rank
                rank_trend = f'<span style="color:green">↑ {prev_rank - curr_rank}</span>'
            elif curr_rank > prev_rank: # Dropped rank
                rank_trend = f'<span style="color:red">↓ {curr_rank - prev_rank}</span>'
        
        data["rank_trend"] = rank_trend
        report_data.append(data)

    # Sort final report by Rank
    report_data.sort(key=lambda x: x["rank"])

    return report_data

def calculate_scores_and_ranks(employee_list, start_date, end_date, settings, employees_meta, standard_working_days):
    attendance_records = frappe.get_all(
        "Attendance",
        filters={
            "employee": ["in", employee_list],
            "attendance_date": ["between", [start_date, end_date]],
            "docstatus": 1
        },
        fields=["employee", "attendance_date", "status", "leave_type"]
    )
    
    att_map = {}
    for att in attendance_records:
        if att.employee not in att_map: att_map[att.employee] = []
        att_map[att.employee].append(att)

    checkin_records = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": ["in", employee_list],
            "time": ["between", [get_datetime(f"{start_date} 00:00:00"), get_datetime(f"{end_date} 23:59:59")]],
            "skip_auto_attendance": 0
        },
        fields=["employee", "time", "log_type"],
        order_by="time asc"
    )
    
    checkin_map = {}
    for checkin in checkin_records:
        date_str = str(checkin.time.date())
        emp = checkin.employee
        if emp not in checkin_map: checkin_map[emp] = {}
        if date_str not in checkin_map[emp]: checkin_map[emp][date_str] = []
        checkin_map[emp][date_str].append(checkin)

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
        # WFH Exclusion
        if settings.enable_wfh_exclusion:
            is_wfh_only = False
            if id_pattern and id_pattern in str(emp.employee_number or "").upper(): is_wfh_only = True
            if not is_wfh_only and emp.branch in excluded_branches: is_wfh_only = True
            if not is_wfh_only and emp.employment_type in excluded_employment_types: is_wfh_only = True
            if is_wfh_only: continue

        emp_att = att_map.get(emp.name, [])
        emp_checkins = checkin_map.get(emp.name, {})

        stats = {
            "present_days": 0, "half_days": 0, "leave_days": 0, "wfh_days": 0,
            "absent_days": 0, "lwp_days": 0, "total_working_days": len(emp_att),
            "late_arrival_count": 0, "severe_late_count": 0,
            "actual_work_seconds": 0
        }
        
        score = settings.base_score
        
        for att in emp_att:
            status = att.status
            date_str = str(att.attendance_date)
            
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
                
            if date_str in emp_checkins:
                day_logs = emp_checkins[date_str]
                checkin_time = day_logs[0].time.time()
                
                # 1. Punctuality
                if checkin_time >= settings.office_start_time:
                    diff = datetime.datetime.combine(datetime.date.min, checkin_time) - \
                           datetime.datetime.combine(datetime.date.min, settings.office_start_time)
                    if (diff.total_seconds() / 60) > settings.late_grace_period:
                        stats["late_arrival_count"] += 1
                        if checkin_time <= settings.severe_late_threshold: score -= settings.standard_late_penalty
                        else:
                            score -= settings.severe_late_penalty
                            stats["severe_late_count"] += 1

                # 2. Duration Logic (Always calculated to accumulate Actual Hours)
                day_work_seconds = 0
                day_clusters = []
                for log_type, group in groupby(day_logs, key=lambda x: x.log_type):
                    day_clusters.append((log_type, list(group)))
                for i in range(len(day_clusters) - 1):
                    if day_clusters[i][0] == "IN" and day_clusters[i+1][0] == "OUT":
                        day_work_seconds += (day_clusters[i+1][1][-1].time - day_clusters[i][1][0].time).total_seconds()

                stats["actual_work_seconds"] += day_work_seconds

                # Apply scoring only if enabled
                if settings.enable_duration_scoring:
                    if day_work_seconds >= (settings.work_target_hours * 3600): score += settings.work_bonus
                    if len(day_logs) >= 2:
                        span = (day_logs[-1].time - day_logs[0].time).total_seconds()
                        if (max(span - day_work_seconds, 0)) > (settings.break_threshold_hours * 3600):
                            score -= settings.break_penalty

        if settings.enable_habitual_penalties:
            if stats["severe_late_count"] > settings.habitual_threshold_2: score -= settings.habitual_penalty_2
            elif stats["severe_late_count"] > settings.habitual_threshold_1: score -= settings.habitual_penalty_1

        if settings.enable_rewards and stats["total_working_days"] > 0:
            if stats["late_arrival_count"] == 0: score += settings.punctuality_bonus
            if stats["absent_days"] == 0 and stats["half_days"] == 0 and stats["lwp_days"] == 0: score += settings.consistency_bonus

        # Standard Attendance % calculation
        attendance_percentage = 0
        if standard_working_days > 0:
            attendance_percentage = (stats["present_days"] + stats["wfh_days"] + (stats["half_days"] * 0.5)) / standard_working_days * 100

        # Hour-based metrics
        expected_work_seconds = standard_working_days * 8 * 3600
        expected_present_seconds = stats["present_days"] * 8 * 3600
        
        compliance_percentage = 0
        if expected_present_seconds > 0:
            compliance_percentage = (stats["actual_work_seconds"] / expected_present_seconds) * 100

        # Work Hour Compliance Scoring
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
            "late_arrival_count": stats["late_arrival_count"],
            "severe_late_count": stats["severe_late_count"],
            "final_score": score,
        })

    # Rank the list
    scores_list.sort(key=lambda x: x["final_score"], reverse=True)
    
    results_map = {}
    for i, item in enumerate(scores_list):
        item["rank"] = i + 1
        results_map[item["employee"]] = item

    return results_map

def format_duration_short(seconds):
    if seconds <= 0:
        return "0h 00m"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m:02d}m"

def get_standard_working_days(start_date, end_date):
    holidays = frappe.get_all('Holiday', 
        filters={
            'parent': '2026', 
            'holiday_date': ['between', [start_date, end_date]]
        }, 
        fields=['holiday_date', 'weekly_off']
    )
    holiday_dates = {h.holiday_date for h in holidays}
    working_days = 0
    curr_date = getdate(start_date)
    while curr_date <= getdate(end_date):
        if curr_date not in holiday_dates and curr_date.weekday() != 6:
            working_days += 1
        curr_date = add_days(curr_date, 1)
    return working_days

def get_employees(filters):
    conditions = {"status": "Active"}
    if filters.get("department"): conditions["department"] = filters.get("department")
    if filters.get("branch"): conditions["branch"] = filters.get("branch")
    if filters.get("employee"): conditions["name"] = filters.get("employee")
        
    return frappe.get_all(
        "Employee",
        filters=conditions,
        fields=["name", "employee_name", "department", "employee_number", "branch", "employment_type"]
    )
