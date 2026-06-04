import frappe
from frappe import _
from frappe.utils import getdate, add_days, get_datetime, add_months
from itertools import groupby

@frappe.whitelist()
def get_dashboard_data(employee, month_name, year):
    if not employee or not month_name or not year:
        return {}

    month_map = {
        "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
        "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
    }
    month = month_map.get(month_name)

    start_date = getdate(f"{year}-{month}-01")
    end_date = add_days(add_months(start_date, 1), -1)

    # Find the correct employee ID if name is passed
    employees = frappe.get_all("Employee", filters={"name": employee}, pluck="name")
    if not employees:
        employees = frappe.get_all("Employee", filters={"employee_name": ["like", f"%{employee}%"]}, pluck="name")
    
    if not employees:
        return {}
    
    employee_id = employees[0]

    # 1. Fetch Logs
    logs = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee_id,
            "time": ["between", [get_datetime(f"{start_date} 00:00:00"), get_datetime(f"{end_date} 23:59:59")]],
            "skip_auto_attendance": 0
        },
        fields=["time", "log_type"],
        order_by="time asc"
    )

    # 2. Fetch Attendance
    attendance = frappe.get_all("Attendance",
        filters={
            "employee": employee_id,
            "attendance_date": ["between", [start_date, end_date]],
            "docstatus": 1
        },
        fields=["attendance_date", "status", "leave_type"]
    )
    att_map = {str(a.attendance_date): a for a in attendance}

    # 3. Process Daily Data
    daily_logs = {}
    for log in logs:
        date_str = str(log.time.date())
        daily_logs.setdefault(date_str, []).append(log)

    all_leave_types = frappe.get_all("Leave Type", pluck="name")
    
    counts = {"Present": 0, "Absent": 0, "Half Day": 0, "Work From Home": 0, "On Leave": 0}
    leave_type_counts = {lt: 0 for lt in all_leave_types}
    
    report_data = []
    chart_labels = []
    chart_values = []

    curr_date = start_date
    while curr_date <= end_date:
        date_str = str(curr_date)
        day_logs = daily_logs.get(date_str, [])
        att_row = att_map.get(date_str)
        
        status = att_row.status if att_row else ""
        leave_type = att_row.leave_type if att_row else ""

        if status:
            if status == "Present": counts["Present"] += 1
            elif status == "Absent": counts["Absent"] += 1
            elif status == "Half Day": counts["Half Day"] += 1
            elif "Work From Home" in status or "WFH" in status: counts["Work From Home"] += 1
            
            if "Leave" in status:
                counts["On Leave"] += 1
                if leave_type in leave_type_counts:
                    leave_type_counts[leave_type] += 1

        work_seconds = 0
        first_in = None
        last_out = None
        if day_logs:
            first_in = day_logs[0].time.strftime("%H:%M")
            last_out = day_logs[-1].time.strftime("%H:%M")
            
            clusters = []
            for log_type, group in groupby(day_logs, key=lambda x: x.log_type):
                clusters.append((log_type, list(group)))
            for i in range(len(clusters) - 1):
                if clusters[i][0] == "IN" and clusters[i+1][0] == "OUT":
                    work_seconds += (clusters[i+1][1][-1].time - clusters[i][1][0].time).total_seconds()

        work_hours = round(work_seconds / 3600.0, 2)
        
        report_data.append({
            "date": date_str,
            "status": status,
            "leave_type": leave_type,
            "first_in": first_in or "-",
            "last_out": last_out or "-",
            "work_hours": f"{int(work_seconds//3600)}h {int((work_seconds%3600)//60):02d}m"
        })
        
        chart_labels.append(date_str.split("-")[-1])
        chart_values.append(min(work_hours, 15.0))

        curr_date = add_days(curr_date, 1)

    return {
        "report_data": report_data,
        "counts": counts,
        "leave_type_counts": {k: v for k, v in leave_type_counts.items() if v > 0 or k in ["Privilege Leave", "Sick Leave", "Casual Leave", "Leave Without Pay"]},
        "chart_data": {
            "labels": chart_labels,
            "values": chart_values
        }
    }
