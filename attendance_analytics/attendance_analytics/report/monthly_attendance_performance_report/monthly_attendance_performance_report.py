import frappe
from frappe import _
from frappe.utils import getdate, add_days, get_datetime, now_datetime
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
        {"label": _("Employee ID"), "fieldname": "employee_id", "fieldtype": "Data", "width": 100},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
        {"label": _("Total Working Days"), "fieldname": "total_working_days", "fieldtype": "Int", "width": 130},
        {"label": _("Present Days"), "fieldname": "present_days", "fieldtype": "Int", "width": 100},
        {"label": _("Half Days"), "fieldname": "half_days", "fieldtype": "Int", "width": 90},
        {"label": _("Leave Days"), "fieldname": "leave_days", "fieldtype": "Int", "width": 90},
        {"label": _("WFH Days"), "fieldname": "wfh_days", "fieldtype": "Int", "width": 90},
        {"label": _("Absent Days"), "fieldname": "absent_days", "fieldtype": "Int", "width": 100},
        {"label": _("Attendance %"), "fieldname": "attendance_percentage", "fieldtype": "Percent", "width": 110},
        {"label": _("Late Arrival Count"), "fieldname": "late_arrival_count", "fieldtype": "Int", "width": 130},
        {"label": _("Severe Late Count"), "fieldname": "severe_late_count", "fieldtype": "Int", "width": 140},
        {"label": _("Final Score"), "fieldname": "final_score", "fieldtype": "Float", "width": 110},
    ]

def get_data(filters, settings):
    month = filters.get("month")
    year = filters.get("year")
    
    if not month or not year:
        return []

    # Get start and end dates
    start_date = getdate(f"{year}-{month}-01")
    if int(month) == 12:
        end_date = add_days(getdate(f"{int(year)+1}-01-01"), -1)
    else:
        end_date = add_days(getdate(f"{year}-{int(month)+1}-01"), -1)

    today = getdate(now_datetime())
    if end_date > today:
        end_date = today

    employees = get_employees(filters)
    employee_list = [e.name for e in employees]
    
    if not employee_list:
        return []

    # Fetch attendance
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
        if att.employee not in att_map:
            att_map[att.employee] = []
        att_map[att.employee].append(att)

    # Fetch checkins
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
        if emp not in checkin_map:
            checkin_map[emp] = {}
        if date_str not in checkin_map[emp]:
            checkin_map[emp][date_str] = []
        checkin_map[emp][date_str].append(checkin)

    report_data = []
    
    leave_penalties = {
        "Privilege Leave": settings.privilege_leave_penalty,
        "Sick Leave": settings.sick_leave_penalty,
        "Casual Leave": settings.casual_leave_penalty,
        "Maternity Leave": settings.maternity_leave_penalty,
        "Compensatory Off": settings.comp_off_penalty,
        "Holiday Duty": settings.holiday_duty_penalty,
        "Leave Without Pay": settings.lwp_penalty
    }

    for emp in employees:
        # WFH Exclusion
        if settings.enable_wfh_exclusion:
            is_wfh_only = False
            if emp.employee_number and "WFH" in str(emp.employee_number).upper():
                is_wfh_only = True
            elif emp.branch == "RIS - US":
                is_wfh_only = True
            elif emp.employment_type and "WFH" in str(emp.employment_type).upper():
                is_wfh_only = True

            if is_wfh_only:
                continue

        emp_att = att_map.get(emp.name, [])
        emp_checkins = checkin_map.get(emp.name, {})

        stats = {
            "present_days": 0,
            "half_days": 0,
            "leave_days": 0,
            "wfh_days": 0,
            "absent_days": 0,
            "lwp_days": 0,
            "total_working_days": len(emp_att),
            "late_arrival_count": 0,
            "severe_late_count": 0,
        }
        
        score = settings.base_score
        
        for att in emp_att:
            status = att.status
            date_str = str(att.attendance_date)
            
            # Attendance Penalties
            if status == "Present":
                stats["present_days"] += 1
            elif status == "Half Day":
                stats["half_days"] += 1
                score -= settings.half_day_penalty
            elif "Leave" in status:
                stats["leave_days"] += 1
                if att.leave_type == "Leave Without Pay":
                    stats["lwp_days"] += 1
                penalty = leave_penalties.get(att.leave_type, settings.default_leave_penalty)
                score -= penalty
            elif "Work From Home" in status or "WFH" in status:
                stats["wfh_days"] += 1
                score -= settings.wfh_status_penalty
            elif status == "Absent":
                stats["absent_days"] += 1
                score -= settings.absent_penalty
                
            # Biometric-based Scoring (Punctuality & Duration)
            if date_str in emp_checkins:
                day_logs = emp_checkins[date_str]
                first_log = day_logs[0]
                checkin_time = first_log.time.time()
                
                # 1. Punctuality
                if checkin_time >= settings.office_start_time:
                    diff = datetime.datetime.combine(datetime.date.min, checkin_time) - \
                           datetime.datetime.combine(datetime.date.min, settings.office_start_time)
                    late_minutes = diff.total_seconds() / 60
                    
                    if late_minutes > settings.late_grace_period:
                        stats["late_arrival_count"] += 1
                        
                        if checkin_time <= settings.severe_late_threshold:
                            score -= settings.standard_late_penalty
                        else:
                            score -= settings.severe_late_penalty
                            stats["severe_late_count"] += 1

                # 2. Optional Duration Scoring
                if settings.enable_duration_scoring:
                    day_work_seconds = 0
                    day_break_seconds = 0
                    
                    day_clusters = []
                    for log_type, group in groupby(day_logs, key=lambda x: x.log_type):
                        day_clusters.append((log_type, list(group)))
                    
                    for i in range(len(day_clusters) - 1):
                        if day_clusters[i][0] == "IN" and day_clusters[i+1][0] == "OUT":
                            start_t = day_clusters[i][1][0].time
                            end_t = day_clusters[i+1][1][-1].time
                            day_work_seconds += (end_t - start_t).total_seconds()

                    if len(day_logs) >= 2:
                        span = (day_logs[-1].time - day_logs[0].time).total_seconds()
                        day_break_seconds = max(span - day_work_seconds, 0)

                    # Work Bonus
                    if day_work_seconds >= (settings.work_target_hours * 3600):
                        score += settings.work_bonus
                    
                    # Break Penalty
                    if day_break_seconds > (settings.break_threshold_hours * 3600):
                        score -= settings.break_penalty

        # Habitual Penalties
        if settings.enable_habitual_penalties:
            if stats["severe_late_count"] > settings.habitual_threshold_2:
                score -= settings.habitual_penalty_2
            elif stats["severe_late_count"] > settings.habitual_threshold_1:
                score -= settings.habitual_penalty_1

        # Monthly Rewards
        if settings.enable_rewards and stats["total_working_days"] > 0:
            if stats["late_arrival_count"] == 0:
                score += settings.punctuality_bonus
            
            if stats["absent_days"] == 0 and stats["half_days"] == 0 and stats["lwp_days"] == 0:
                score += settings.consistency_bonus

        if score < 0: score = 0
        
        att_percentage = 0
        if stats["total_working_days"] > 0:
            att_percentage = (stats["present_days"] + stats["wfh_days"] + (stats["half_days"] * 0.5)) / stats["total_working_days"] * 100

        display_emp_id = str(emp.name).split(":")[0].strip()

        row = {
            "employee": emp.name,
            "employee_id": display_emp_id,
            "employee_name": emp.employee_name,
            "department": emp.department,
            "total_working_days": stats["total_working_days"],
            "present_days": stats["present_days"],
            "half_days": stats["half_days"],
            "leave_days": stats["leave_days"],
            "wfh_days": stats["wfh_days"],
            "absent_days": stats["absent_days"],
            "attendance_percentage": att_percentage,
            "late_arrival_count": stats["late_arrival_count"],
            "severe_late_count": stats["severe_late_count"],
            "final_score": score,
        }
        report_data.append(row)

    report_data.sort(key=lambda x: x["final_score"], reverse=True)
    
    final_data = []
    rank = 1
    for r in report_data:
        r["rank"] = rank
        final_data.append(r)
        rank += 1

    return final_data

def get_employees(filters):
    conditions = {"status": "Active"}
    if filters.get("department"):
        conditions["department"] = filters.get("department")
    if filters.get("branch"):
        conditions["branch"] = filters.get("branch")
    if filters.get("employee"):
        conditions["name"] = filters.get("employee")
        
    return frappe.get_all(
        "Employee",
        filters=conditions,
        fields=["name", "employee_name", "department", "employee_number", "branch", "employment_type"]
    )
