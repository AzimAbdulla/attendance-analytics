"""
DAILY WORK DURATION REPORT
--------------------------
Provides a high-speed breakdown of work and break hours for all active
employees on a single specific day. 

Designed for quick operational morning audits.
"""

import frappe
from frappe import _
from attendance_analytics.attendance_analytics.report.monthly_attendance_performance_report.monthly_attendance_performance_report import get_settings

def execute(filters=None):
    """Entry point returning (columns, data)."""
    if not filters:
        filters = {}

    settings = get_settings()
    columns = get_columns()
    data = get_data(filters, settings)
    
    return columns, data

def get_columns():
    """Defines the 5 basic columns for daily physical presence."""
    return [
        {"label": _("ID"), "fieldname": "employee_id", "fieldtype": "Data", "width": 100},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 150},
        {"label": _("Work Duration"), "fieldname": "work_duration", "fieldtype": "Data", "width": 140},
        {"label": _("Break Duration"), "fieldname": "break_duration", "fieldtype": "Data", "width": 140},
    ]

def get_data(filters, settings):
    """
    Core logic. Processes all active employees for the selected 'date'.
    Applies WFH exclusion logic to hide certain staff segments.
    """
    # date (str): Target day in YYYY-MM-DD format.
    date = filters.get("date")
    if not date:
        return []

    # Target active employees only
    emp_filters = {"status": "Active"}
    if filters.get("department"): emp_filters["department"] = filters.get("department")
    if filters.get("employee"): emp_filters["name"] = filters.get("employee")

    employees = frappe.get_all(
        "Employee",
        filters=emp_filters,
        fields=["name", "employee_name", "department", "employee_number", "branch", "employment_type"]
    )
    
    employee_list = [e.name for e in employees]
    if not employee_list:
        return []

    # Fetch biometric punches for the entire company for this one day
    logs = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": ["in", employee_list],
            "time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]
        },
        fields=["employee", "time", "log_type"],
        order_by="employee, time asc"
    )

    # emp_logs (dict): Clusters raw logs by employee ID for constant-time lookup.
    emp_logs = {}
    for log in logs:
        emp_logs.setdefault(log.employee, []).append(log)

    report_data = []

    # Prepare exclusion criteria from global settings
    excluded_branches = [b.branch for b in settings.excluded_branches]
    excluded_employment_types = [t.employment_type for t in settings.excluded_employment_types]
    id_pattern = (settings.excluded_id_pattern or "").upper()

    for emp in employees:
        # --- EXCLUSION LOGIC ---
        if settings.enable_wfh_exclusion:
            is_excluded = False
            if id_pattern and id_pattern in str(emp.employee_number or "").upper(): is_excluded = True
            if not is_excluded and emp.branch in excluded_branches: is_excluded = True
            if not is_excluded and emp.employment_type in excluded_employment_types: is_excluded = True
            if is_excluded: continue

        logs = emp_logs.get(emp.name, [])
        if not logs: continue # Skip employees who didn't punch in

        work_seconds = break_seconds = 0
        
        # --- CLUSTERED GREEDY DURATION LOGIC ---
        from itertools import groupby
        clusters = []
        # Group punch sequences: [IN, IN, OUT] -> [(IN, [log, log]), (OUT, [log])]
        for log_type, group in groupby(logs, key=lambda x: x.log_type):
            clusters.append((log_type, list(group)))

        for i in range(len(clusters) - 1):
            if clusters[i][0] == "IN" and clusters[i+1][0] == "OUT":
                # Start = First punch of IN-cluster | End = Last punch of OUT-cluster
                start_time = clusters[i][1][0].time
                end_time = clusters[i+1][1][-1].time
                work_seconds += (end_time - start_time).total_seconds()

        # --- SPAN & BREAK CALCULATION ---
        if len(logs) >= 2:
            total_span = (logs[-1].time - logs[0].time).total_seconds()
            break_seconds = max(total_span - work_seconds, 0)

        # display_emp_id (str): Formatted ID (removes the name part if using autoname).
        display_emp_id = str(emp.name).split(":")[0].strip()

        report_data.append({
            "employee": emp.name,
            "employee_id": display_emp_id,
            "employee_name": emp.employee_name,
            "department": emp.department,
            "work_duration": format_duration(work_seconds),
            "break_duration": format_duration(break_seconds)
        })

    return report_data

def format_duration(seconds):
    """Formats raw seconds into 'Xh Ym'."""
    if seconds <= 0: return "0h 0m"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m}m"

# ==============================================================================
# WARNINGS & CRITICAL DEPENDENCIES
# ==============================================================================
# 1. SHARED LOGIC: This report imports 'get_settings' from the Monthly 
#    Performance Report. Modifying that file's export will break this report.
#
# 2. DATA SCALE: This report handles all employees in one query. Expanding
#    the date range filter beyond a single day may lead to query timeouts.
#
# 3. SETTINGS: Relies on 'Attendance Performance Settings' for exclusion rules.
# ==============================================================================
