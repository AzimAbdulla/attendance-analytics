import frappe
from frappe.utils import now_datetime, add_to_date

def check_missed_heartbeats():
    """Scheduled job running every 5 minutes to close stale sessions."""
    now = now_datetime()
    # 15 minutes ago
    cutoff_time = add_to_date(now, minutes=-3)
    
    # Find active sessions with missed heartbeats
    stale_sessions = frappe.get_all(
        "WFH Session", 
        filters={
            "status": "Active",
            "last_heartbeat": ["<", cutoff_time]
        },
        fields=["name", "employee", "last_heartbeat", "device_id"]
    )
    
    for session in stale_sessions:
        # Create Checkin OUT at the time of the last successful heartbeat
        checkin = frappe.get_doc({
            "doctype": "Employee Checkin",
            "employee": session.employee,
            "log_type": "OUT",
            "time": session.last_heartbeat,
            "device_id": session.device_id
        })
        checkin.insert(ignore_permissions=True)
        
        # Close the Session
        frappe.db.set_value("WFH Session", session.name, {
            "status": "Closed",
            "session_end": session.last_heartbeat
        })
        
    frappe.db.commit()
