# Copyright (c) 2026, Azim Abdulla and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, add_days, get_datetime, add_months
from itertools import groupby

def execute(filters=None):
    if not filters:
        filters = {}

    if not filters.get("employee") or not filters.get("month") or not filters.get("year"):
        return [], []

    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)

    return columns, data, None, chart

def get_chart(data):
    if not data:
        return None

    # Filter out styled HTML and extract just the Day for legibility
    labels = []
    for d in data:
        date_str = d["date"]
        if "<span" in str(date_str):
            # Extract date from span: <span ...>2026-01-01</span>
            date_str = date_str.split(">")[1].split("<")[0]
        
        # Use just the day number (YYYY-MM-DD -> DD)
        day_label = date_str.split("-")[-1]
        labels.append(day_label)

    def get_hours(duration_str):
        # Format is "Xh Ym"
        try:
            parts = duration_str.split(" ")
            h = float(parts[0].replace("h", ""))
            m = float(parts[1].replace("m", ""))
            return round(h + (m / 60.0), 2)
        except:
            return 0

    values = [min(get_hours(d["work_duration"]), 15.0) for d in data]

    chart = {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": _("Work Duration (Hours)"),
                    "values": values
                }
            ]
        },
        "type": "line",
        "colors": ["#7cd6fd"],
        "axisOptions": {
            "xIsSeries": 1,
            "yAxisMode": "tick",
            "maxValue": 15
        }
    }

    return chart

def get_columns():
    return [
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Data", "width": 120},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": _("Leave Type"), "fieldname": "leave_type", "fieldtype": "Data", "width": 140},
        {"label": _("First In"), "fieldname": "first_in", "fieldtype": "Time", "width": 110},
        {"label": _("Last Out"), "fieldname": "last_out", "fieldtype": "Time", "width": 110},
        {"label": _("Span Duration"), "fieldname": "span_duration", "fieldtype": "Data", "width": 140},
        {"label": _("Work Duration"), "fieldname": "work_duration", "fieldtype": "Data", "width": 140},
        {"label": _("Break Duration"), "fieldname": "break_duration", "fieldtype": "Data", "width": 140},
    ]

def get_data(filters):
    emp_input = filters.get("employee")
    month_name = filters.get("month")
    year = filters.get("year")

    month_map = {
        "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
        "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
    }
    month = month_map.get(month_name)

    start_date = getdate(f"{year}-{month}-01")
    end_date = add_days(add_months(start_date, 1), -1)

    employee_id = emp_input
    if emp_input:
        employees = frappe.get_all("Employee", filters={"name": emp_input}, pluck="name")
        if not employees:
            employees = frappe.get_all("Employee", filters={"employee_name": ["like", f"%{emp_input}%"]}, pluck="name")
        
        if employees:
            employee_id = employees[0]
        else:
            return []

    # Fetch checkins for the selected employee and month
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

    # Fetch holidays
    holidays = frappe.get_all('Holiday', 
        filters={
            'parent': '2026', 
            'holiday_date': ['between', [start_date, end_date]]
        }, 
        fields=['holiday_date']
    )
    holiday_dates = {str(h.holiday_date) for h in holidays}

    # Fetch attendance
    attendance = frappe.get_all("Attendance",
        filters={
            "employee": employee_id,
            "attendance_date": ["between", [start_date, end_date]],
            "docstatus": 1
        },
        fields=["attendance_date", "status", "leave_type"]
    )
    att_map = {str(a.attendance_date): a for a in attendance}

    # Group logs by date
    daily_logs = {}
    for log in logs:
        date_str = str(log.time.date())
        if date_str not in daily_logs:
            daily_logs[date_str] = []
        daily_logs[date_str].append(log)

    report_data = []

    # Iterate through each day of the month in chronological order
    curr_date = start_date
    while curr_date <= end_date:
        date_str = str(curr_date)
        day_logs = daily_logs.get(date_str, [])
        att_row = att_map.get(date_str)
        
        status = att_row.status if att_row else ""
        leave_type = att_row.leave_type if att_row else ""

        work_duration = "0h 00m"
        break_duration = "0h 00m"
        span_duration = "0h 00m"
        first_in = None
        last_out = None

        if day_logs:
            first_in = day_logs[0].time.time()
            last_out = day_logs[-1].time.time()
            work_seconds = 0
            
            # 1. Group consecutive logs into clusters
            clusters = []
            for log_type, group in groupby(day_logs, key=lambda x: x.log_type):
                clusters.append((log_type, list(group)))

            # 2. Calculate Work Duration (Clustered Greedy: IN start to OUT end)
            for i in range(len(clusters) - 1):
                if clusters[i][0] == "IN" and clusters[i+1][0] == "OUT":
                    work_seconds += (clusters[i+1][1][-1].time - clusters[i][1][0].time).total_seconds()

            # 3. Calculate Total Span and Break Time
            if len(day_logs) >= 2:
                span_seconds = (day_logs[-1].time - day_logs[0].time).total_seconds()
                span_duration = format_duration_short(span_seconds)
                break_seconds = max(span_seconds - work_seconds, 0)
                break_duration = format_duration_short(break_seconds)
            
            work_duration = format_duration_short(work_seconds)

        display_date = date_str
        if date_str in holiday_dates:
            display_date = f"<span style='color:red; font-weight:bold;'>{date_str}</span>"

        report_data.append({
            "date": display_date,
            "status": status,
            "leave_type": leave_type,
            "first_in": first_in,
            "last_out": last_out,
            "span_duration": span_duration,
            "work_duration": work_duration,
            "break_duration": break_duration
        })

        curr_date = add_days(curr_date, 1)

    return report_data

def format_duration_short(seconds):
    if seconds <= 0:
        return "0h 00m"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m:02d}m"
