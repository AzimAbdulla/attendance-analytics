"""
WFH BACKGROUND TASKS
--------------------
Contains automated jobs that run periodically via the Frappe Scheduler.
Managed through the 'scheduler_events' in hooks.py.
"""

import frappe
from frappe.utils import now_datetime, add_to_date

def check_missed_heartbeats():
    """
    STALE SESSION WATCHDOG
    Runs every 1 minute.
    
    Logic:
    1. Finds all 'WFH Session' documents with status 'Active'.
    2. Compares 'last_heartbeat' against the 3-minute cutoff.
    3. If an employee's machine has stopped sending signals, it auto-logs them out.
    """
    now = now_datetime()
    
    # cutoff_time (datetime): Current time minus 3 minutes.
    # Sessions with heartbeats older than this are considered 'Disconnected'.
    cutoff_time = add_to_date(now, minutes=-3)
    
    stale_sessions = frappe.get_all(
        "WFH Session", 
        filters={
            "status": "Active",
            "last_heartbeat": ["<", cutoff_time]
        },
        fields=["name", "employee", "last_heartbeat", "device_id"]
    )
    
    for session in stale_sessions:
        # Create an official 'OUT' log to stop the attendance timer.
        # We use the time of the LAST successful heartbeat for accuracy.
        checkin = frappe.get_doc({
            "doctype": "Employee Checkin",
            "employee": session.employee,
            "log_type": "OUT",
            "time": session.last_heartbeat,
            "device_id": session.device_id
        })
        checkin.insert(ignore_permissions=True)
        
        # Formally close the tracking session.
        frappe.db.set_value("WFH Session", session.name, {
            "status": "Closed",
            "session_end": session.last_heartbeat
        })
        
    frappe.db.commit()
