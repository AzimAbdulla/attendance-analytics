import frappe
from frappe import _
from frappe.utils import getdate, add_days, get_datetime, now_datetime
import datetime

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    
    return columns, data, None, chart

def get_chart(data):
    if not data:
        return None

    # Top 10 Scores (excluding WFH if they have no rank, or just top 10 from final data)
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

def get_data(filters):
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

    # Current date handling for partial month
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
    
    # Map attendance by employee
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
    
    # Map checkins by employee and date
    checkin_map = {}
    for checkin in checkin_records:
        date_str = str(checkin.time.date())
        emp = checkin.employee
        if emp not in checkin_map:
            checkin_map[emp] = {}
        if date_str not in checkin_map[emp]:
            checkin_map[emp][date_str] = []
        checkin_map[emp][date_str].append(checkin.time)

    report_data = []
    
    office_start_str = "09:00:00"
    office_start_time = datetime.datetime.strptime(office_start_str, "%H:%M:%S").time()

    leave_penalties = {
        "Privilege Leave": 1,
        "Sick Leave": 2,
        "Casual Leave": 2,
        "Maternity Leave": 0,
        "Compensatory Off": 0,
        "Holiday Duty": 0,
        "Leave Without Pay": 5
    }

    for emp in employees:
        # Check if WFH employee based on Employee Number (ESSL), Branch, or Employment Type
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
        
        score = 100.0
        
        for att in emp_att:
            status = att.status
            date_str = str(att.attendance_date)
            
            # Attendance Penalties
            if status == "Present":
                stats["present_days"] += 1
            elif status == "Half Day":
                stats["half_days"] += 1
                score -= 3
            elif "Leave" in status:
                stats["leave_days"] += 1
                if att.leave_type == "Leave Without Pay":
                    stats["lwp_days"] += 1
                penalty = leave_penalties.get(att.leave_type, 4)
                score -= penalty
            elif "Work From Home" in status or "WFH" in status:
                stats["wfh_days"] += 1
                score -= 2
            elif status == "Absent":
                stats["absent_days"] += 1
                score -= 6
                
            # Punctuality Penalties (only if Present or Half Day or WFH?) 
            # Usually only if they checked in.
            if date_str in emp_checkins:
                first_checkin = emp_checkins[date_str][0]
                checkin_time = first_checkin.time()
                
                # Check punctuality
                if checkin_time >= office_start_time:
                    # Calculate minutes late
                    diff = datetime.datetime.combine(datetime.date.min, checkin_time) - \
                           datetime.datetime.combine(datetime.date.min, office_start_time)
                    late_minutes = diff.total_seconds() / 60
                    
                    if late_minutes > 10:
                        stats["late_arrival_count"] += 1
                        
                        if late_minutes <= 60:
                            score -= 1
                        else:
                            score -= 2
                            stats["severe_late_count"] += 1

        # Repeated Lateness Penalties (using only Severe Late Arrivals)
        if stats["severe_late_count"] > 10:
            score -= 6
        elif stats["severe_late_count"] > 5:
            score -= 3

        # Apply Rewards
        if stats["total_working_days"] > 0:
            if stats["late_arrival_count"] == 0:
                score += 3
            
            if stats["absent_days"] == 0 and stats["half_days"] == 0 and stats["lwp_days"] == 0:
                score += 5

        # Final Score clamping
        if score < 0: score = 0
        
        # Attendance Percentage
        att_percentage = 0
        if stats["total_working_days"] > 0:
            att_percentage = (stats["present_days"] + stats["wfh_days"] + (stats["half_days"] * 0.5)) / stats["total_working_days"] * 100

        # Get numeric Employee ID if formatted as "36:Jino Thomas"
        display_emp_id = str(emp.name).split(":")[0].strip()

        row = {
            "employee": emp.name, # Hidden link reference if needed
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

    # Sorting and Ranking
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
