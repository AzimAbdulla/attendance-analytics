"""
MONTHLY WORK DURATION REPORT (MWDR)
----------------------------------
This report provides a granular 'Time Sheet' for a single employee. 
It calculates the exact physical presence by processing biometric logs 
and separating productive work time from break time.

Main Use Case: 
This report is typically reached by clicking an Employee's name in the 
'Monthly Employee Attendance Report' (Audit Matrix).
"""

import frappe
from frappe import _
from frappe.utils import getdate, add_days, get_datetime, add_months
from itertools import groupby

def execute(filters=None):
    """
    Main entry point. Validates employee selection and fetches report data.
    
    Returns:
        columns (list): Table headers metadata.
        data (list): Daily work breakdown rows.
        message (None): Not used in this report.
        chart (dict): Line chart config showing work-hour trends.
        summary (list): Card data for the top of the report.
    """
    if not filters:
        filters = {}

    if not filters.get("employee") or not filters.get("month") or not filters.get("year"):
        return [], []

    columns = get_columns()
    data, summary = get_data(filters)
    chart = get_chart(data)

    return columns, data, None, chart, summary

def get_chart(data):
    """
    Generates a trend line chart of work hours over the month.
    
    Arguments:
        data (list): The list of row dictionaries prepared in get_data.
    """
    if not data:
        return None

    # labels (list): Stores day numbers (e.g., 01, 02) for the X-axis.
    labels = []
    for d in data:
        date_str = d["date"]
        # Handle cases where the date is wrapped in HTML for Holiday coloring
        if "<span" in str(date_str):
            date_str = date_str.split(">")[1].split("<")[0]
        
        day_label = date_str.split("-")[-1]
        labels.append(day_label)

    def get_hours(duration_str):
        """Helper to convert 'Xh YYm' strings into float hours for the chart."""
        try:
            parts = duration_str.split(" ")
            h = float(parts[0].replace("h", ""))
            m = float(parts[1].replace("m", ""))
            return round(h + (m / 60.0), 2)
        except:
            return 0

    # values (list): Daily work hour floats for the Y-axis.
    # Capped at 15.0 to prevent outlier punch errors from breaking chart scale.
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
        "colors": ["#3498db"],
        "lineOptions": {"regionFill": 1, "hideDots": 0, "strokeWidth": 3},
        "axisOptions": {"xIsSeries": 1, "yAxisMode": "tick", "maxValue": 15}
    }

    return chart

def get_columns():
    """Defines the 8 columns for the daily breakdown table."""
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
    """
    Main processing logic. 
    Fetches raw logs and applies Clustered Greedy logic for one specific employee.
    """
    emp_input = filters.get("employee")
    month_name = filters.get("month")
    year = filters.get("year")

    # Resolve numerical month
    month_map = {
        "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
        "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
    }
    month = month_map.get(month_name)

    start_date = getdate(f"{year}-{month}-01")
    end_date = add_days(add_months(start_date, 1), -1)

    # Validate employee ID or handle fuzzy name lookup
    employee_id = emp_input
    if emp_input:
        employees = frappe.get_all("Employee", filters={"name": emp_input}, pluck="name")
        if not employees:
            employees = frappe.get_all("Employee", filters={"employee_name": ["like", f"%{emp_input}%"]}, pluck="name")
        
        if employees:
            employee_id = employees[0]
        else:
            return [], []

    # logs (list): All biometric punches for the month.
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

    # holiday_dates (set): Used to identify weekends/holidays for row coloring.
    holidays = frappe.get_all('Holiday', filters={'parent': '2026', 'holiday_date': ['between', [start_date, end_date]]}, fields=['holiday_date'])
    holiday_dates = {str(h.holiday_date) for h in holidays}

    # att_map (dict): Maps date string to official Attendance Doc for status labeling.
    attendance = frappe.get_all("Attendance",
        filters={"employee": employee_id, "attendance_date": ["between", [start_date, end_date]], "docstatus": 1},
        fields=["attendance_date", "status", "leave_type"]
    )
    att_map = {str(a.attendance_date): a for a in attendance}

    # daily_logs (dict): Groups raw logs into { "YYYY-MM-DD": [list of logs] }
    daily_logs = {}
    for log in logs:
        date_str = str(log.time.date())
        daily_logs.setdefault(date_str, []).append(log)

    all_leave_types = frappe.get_all("Leave Type", pluck="name")
    report_data = []
    
    # counts (dict): Aggregator for the summary cards.
    counts = {"Present": 0, "Absent": 0, "Half Day": 0, "Work From Home": 0, "On Leave": 0}
    leave_type_counts = {lt: 0 for lt in all_leave_types}

    # Chronological Processing Loop
    curr_date = start_date
    while curr_date <= end_date:
        date_str = str(curr_date)
        day_logs = daily_logs.get(date_str, [])
        att_row = att_map.get(date_str)
        
        status = att_row.status if att_row else ""
        leave_type = att_row.leave_type if att_row else ""

        if not status and date_str in holiday_dates:
            status = "Holiday"

        # Increment summary counts
        if status:
            if status == "Present": counts["Present"] += 1
            elif status == "Absent": counts["Absent"] += 1
            elif status == "Half Day": counts["Half Day"] += 1
            elif "Work From Home" in status or "WFH" in status: counts["Work From Home"] += 1
            if "Leave" in status:
                counts["On Leave"] += 1
                if leave_type in leave_type_counts: leave_type_counts[leave_type] += 1

        # Logic variables for durations
        work_duration = "0h 00m"
        break_duration = "0h 00m"
        span_duration = "0h 00m"
        first_in = last_out = None

        if day_logs:
            first_in = day_logs[0].time.time()
            last_out = day_logs[-1].time.time()
            work_seconds = 0
            
            # --- CLUSTERED GREEDY LOGIC ---
            # Group consecutive logs (e.g., multiple INs) into sessions
            clusters = []
            for log_type, group in groupby(day_logs, key=lambda x: x.log_type):
                clusters.append((log_type, list(group)))

            for i in range(len(clusters) - 1):
                # Calculate time from first IN of cluster to last OUT of following cluster
                if clusters[i][0] == "IN" and clusters[i+1][0] == "OUT":
                    work_seconds += (clusters[i+1][1][-1].time - clusters[i][1][0].time).total_seconds()

            # --- SPAN & BREAK LOGIC ---
            if len(day_logs) >= 2:
                # span_seconds (float): Total office presence (Absolute Last - Absolute First)
                span_seconds = (day_logs[-1].time - day_logs[0].time).total_seconds()
                span_duration = format_duration_short(span_seconds)
                # Break = Total Office time - Productive Work time
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

    # Post-Loop Filtering
    status_filter = filters.get("status")
    lt_filter = filters.get("leave_type")

    if status_filter or lt_filter:
        filtered_data = []
        for row in report_data:
            match = True
            if status_filter:
                if status_filter == "On Leave" and "Leave" not in row["status"]: match = False
                elif status_filter == "Work From Home" and row["status"] not in ["Work From Home", "WFH"]: match = False
                elif status_filter not in ["On Leave", "Work From Home"] and row["status"] != status_filter: match = False
            if match and lt_filter and row["leave_type"] != lt_filter: match = False
            if match: filtered_data.append(row)
        report_data = filtered_data

    # Generate Summary Card List
    summary = []
    summary.append({"label": _("Present"), "value": counts["Present"], "indicator": "green", "datatype": "Int"})
    summary.append({"label": _("Absent"), "value": counts["Absent"], "indicator": "red", "datatype": "Int"})
    summary.append({"label": _("Half Day"), "value": counts["Half Day"], "indicator": "orange", "datatype": "Int"})
    summary.append({"label": _("WFH"), "value": counts["Work From Home"], "indicator": "blue", "datatype": "Int"})
    for lt, count in leave_type_counts.items():
        if count > 0: # Only show leave types actually taken
            summary.append({"label": _(lt), "value": count, "indicator": "grey", "datatype": "Int"})

    return report_data, summary

def format_duration_short(seconds):
    """Converts seconds into 'Xh YYm' format for report consistency."""
    if seconds <= 0: return "0h 00m"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m:02d}m"


# ==============================================================================
# WARNINGS & CRITICAL DEPENDENCIES
# ==============================================================================
# 1. DRILL-DOWN: The 'employee' filter is pre-filled when routing from the 
#    Audit Matrix. Changing the filter name will break that integration.
#
# 2. YEAR HARDCODE: The 'Holiday' parent is hardcoded to '2026'. Ensure this 
#    is updated annually for accurate holiday identification.
#
# 3. UI COLORING: The Green color for durations is applied in the .js file 
#    based on the 'work_duration' fieldname. If you rename it in Python, 
#    you must update the JS formatter.
# ==============================================================================
