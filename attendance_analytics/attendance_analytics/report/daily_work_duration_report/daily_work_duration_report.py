# Copyright (c) 2026, Azim Abdulla and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)
    
    return columns, data

def get_columns():
    return [
        {"label": _("Employee ID"), "fieldname": "employee_id", "fieldtype": "Data", "width": 100, "fixed": 1},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 180, "fixed": 1},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 150},
        {"label": _("Work Duration"), "fieldname": "work_duration", "fieldtype": "Data", "width": 140},
        {"label": _("Break Duration"), "fieldname": "break_duration", "fieldtype": "Data", "width": 140},
    ]

def get_data(filters):
    date = filters.get("date")
    if not date:
        return []

    # Get employees
    emp_filters = {"status": "Active"}
    if filters.get("department"):
        emp_filters["department"] = filters.get("department")
    if filters.get("employee"):
        emp_filters["name"] = filters.get("employee")

    employees = frappe.get_all(
        "Employee",
        filters=emp_filters,
        fields=["name", "employee_name", "department", "employee_number", "branch", "employment_type"]
    )
    
    employee_list = [e.name for e in employees]
    if not employee_list:
        return []

    # Fetch checkins for the selected date
    logs = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": ["in", employee_list],
            "time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]
        },
        fields=["employee", "time", "log_type"],
        order_by="employee, time asc"
    )

    # Group logs by employee
    emp_logs = {}
    for log in logs:
        if log.employee not in emp_logs:
            emp_logs[log.employee] = []
        emp_logs[log.employee].append(log)

    report_data = []

    for emp in employees:
        # WFH Exclusion Logic
        is_wfh_only = False
        if emp.employee_number and "WFH" in str(emp.employee_number).upper():
            is_wfh_only = True
        elif emp.branch == "RIS - US":
            is_wfh_only = True
        elif emp.employment_type and "WFH" in str(emp.employment_type).upper():
            is_wfh_only = True

        if is_wfh_only:
            continue

        logs = emp_logs.get(emp.name, [])
        work_seconds = 0
        break_seconds = 0
        
        if logs:
            last_time = logs[0].time
            last_type = logs[0].log_type
            
            for i in range(1, len(logs)):
                current_log = logs[i]
                duration = (current_log.time - last_time).total_seconds()
                
                # Strict sequential logic:
                # IN -> OUT = Work
                if last_type == "IN" and current_log.log_type == "OUT":
                    work_seconds += duration
                # OUT -> IN = Break
                elif last_type == "OUT" and current_log.log_type == "IN":
                    break_seconds += duration
                
                # Always update last markers (duplicate INs reset the start time)
                last_time = current_log.time
                last_type = current_log.log_type

        # Format durations
        work_duration = format_duration(work_seconds)
        break_duration = format_duration(break_seconds)

        # Get numeric Employee ID if formatted as "36:Jino Thomas"
        display_emp_id = str(emp.name).split(":")[0].strip()

        report_data.append({
            "employee": emp.name, # Hidden link reference if needed
            "employee_id": display_emp_id,
            "employee_name": emp.employee_name,
            "department": emp.department,
            "work_duration": work_duration,
            "break_duration": break_duration
        })

    return report_data

def format_duration(seconds):
    if seconds <= 0:
        return "0h 0m"
    
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m}m"
