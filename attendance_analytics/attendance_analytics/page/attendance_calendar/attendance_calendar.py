import frappe
from frappe import _
from frappe.utils import getdate, add_days, get_datetime, add_months, cint
from itertools import groupby
from calendar import monthrange

@frappe.whitelist()
def get_calendar_data(employee, month, year):
    if not employee or not month or not year:
        return {}

    # 1. Date Range Setup
    month = cint(month)
    year = cint(year)
    start_date = getdate(f"{year}-{month}-01")
    last_day = monthrange(year, month)[1]
    end_date = getdate(f"{year}-{month}-{last_day}")

    # Permissions: If not HR/Admin, only show self
    current_user = frappe.session.user
    if "System Manager" not in frappe.get_roles() and "HR Manager" not in frappe.get_roles():
        emp_id = frappe.db.get_value("Employee", {"user_id": current_user}, "name")
        if emp_id != employee:
            employee = emp_id

    # 2. Fetch Data
    # Attendance
    attendance = frappe.get_all("Attendance",
        filters={"employee": employee, "attendance_date": ["between", [start_date, end_date]], "docstatus": 1},
        fields=["attendance_date", "status", "leave_type"]
    )
    att_map = {a.attendance_date: a for a in attendance}

    # Checkins
    logs = frappe.get_all("Employee Checkin",
        filters={"employee": employee, "time": ["between", [get_datetime(f"{start_date} 00:00:00"), get_datetime(f"{end_date} 23:59:59")]], "skip_auto_attendance": 0},
        fields=["time", "log_type", "device_id"],
        order_by="time asc",
        limit=0
    )
    daily_logs = {}
    for log in logs:
        date_obj = log.time.date()
        daily_logs.setdefault(date_obj, []).append(log)

    # Holidays
    holiday_list = frappe.db.get_value("Employee", employee, "holiday_list") or \
                   frappe.get_cached_value("Company", frappe.db.get_value("Employee", employee, "company"), "default_holiday_list")
    holidays = frappe.get_all("Holiday",
        filters={"parent": holiday_list, "holiday_date": ["between", [start_date, end_date]]},
        fields=["holiday_date", "weekly_off"]
    )
    holiday_map = {h.holiday_date: "Weekly Off" if h.weekly_off else "Holiday" for h in holidays}

    # Leave Requests (Open/Submitted)
    leave_apps = frappe.get_all("Leave Application",
        filters={"employee": employee, "from_date": ["<=", end_date], "to_date": [">=", start_date], "docstatus": ["<", 2], "status": ["not in", ["Rejected", "Cancelled"]]},
        fields=["from_date", "to_date", "leave_type", "name"]
    )
    leave_app_map = {}
    for app in leave_apps:
        curr = max(app.from_date, start_date)
        last = min(app.to_date, end_date)
        while curr <= last:
            leave_app_map[curr] = {"type": app.leave_type, "id": app.name}
            curr = add_days(curr, 1)

    # 3. Process each day
    days_data = {}
    curr = start_date
    while curr <= end_date:
        day_info = {
            "status": "",
            "abbr": "",
            "work_duration": "0h 00m",
            "break_duration": "0h 00m",
            "is_audit": False,
            "logs": [],
            "clusters": [],
            "work_hours": 0
        }

        att = att_map.get(curr)
        h_status = holiday_map.get(curr)
        day_logs = daily_logs.get(curr, [])
        l_app = leave_app_map.get(curr)

        # Determine Main Status
        if att:
            day_info["status"] = att.status
            if att.status == "On Leave":
                day_info["status"] = f"Leave ({att.leave_type})"
        elif h_status:
            day_info["status"] = h_status
        elif l_app:
            day_info["status"] = f"Leave Requested ({l_app['type']})"
            day_info["is_audit"] = True
        elif day_logs:
            day_info["status"] = "Present (Unmarked)"
            day_info["is_audit"] = True
        else:
            day_info["status"] = "Unmarked"

        # Duration Calculation (Clustered Greedy)
        if day_logs:
            for l in day_logs:
                day_info["logs"].append({
                    "time": l.time.strftime("%H:%M:%S"),
                    "type": l.log_type,
                    "device": l.device_id or "-"
                })

            clusters = []
            for log_type, group in groupby(day_logs, key=lambda x: x.log_type):
                clusters.append({"type": log_type, "logs": list(group)})
            
            work_seconds = 0
            for i in range(len(clusters) - 1):
                if clusters[i]["type"] == "IN" and clusters[i+1]["type"] == "OUT":
                    start_t = clusters[i]["logs"][0].time
                    end_t = clusters[i+1]["logs"][-1].time
                    duration = (end_t - start_t).total_seconds()
                    work_seconds += duration
                    day_info["clusters"].append({
                        "in": start_t.strftime("%H:%M"),
                        "out": end_t.strftime("%H:%M"),
                        "duration": format_duration_short(duration)
                    })
            
            # Fallback
            if work_seconds <= 0 and ("Present" in day_info["status"] or "WFH" in day_info["status"]):
                work_seconds = (day_logs[-1].time - day_logs[0].time).total_seconds()
                day_info["clusters"].append({
                    "in": day_logs[0].time.strftime("%H:%M"),
                    "out": day_logs[-1].time.strftime("%H:%M"),
                    "duration": format_duration_short(work_seconds),
                    "note": "Fallback (Last OUT - First IN)"
                })

            span_seconds = (day_logs[-1].time - day_logs[0].time).total_seconds()
            break_seconds = max(0, span_seconds - work_seconds)
            
            day_info["work_duration"] = format_duration_short(work_seconds)
            day_info["break_duration"] = format_duration_short(break_seconds)
            day_info["work_hours"] = round(work_seconds / 3600.0, 2)

        days_data[str(curr)] = day_info
        curr = add_days(curr, 1)

    return {
        "days": days_data,
        "employee_name": frappe.db.get_value("Employee", employee, "employee_name"),
        "company": frappe.db.get_value("Employee", employee, "company")
    }

def format_duration_short(seconds):
    if seconds <= 0: return "0h 00m"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m:02d}m"
