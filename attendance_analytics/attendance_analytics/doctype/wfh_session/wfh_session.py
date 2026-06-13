"""
WFH SESSION CONTROLLER
----------------------
Manages the server-side lifecycle of a real-time Work From Home session.
Used specifically by the automated heartbeat and auto-logout logic.
"""

from frappe.model.document import Document

class WFHSession(Document):
    """
    Variables:
    - employee (link): Official ID of the remote staff.
    - device_id (data): Identification of the desktop agent machine.
    - session_start (datetime): First 'Check-In' time.
    - session_end (datetime): 'Check-Out' or 'Auto-Logout' time.
    - last_heartbeat (datetime): Most recent signal received from desktop.
    - status (select): 'Active', 'Disconnected', or 'Closed'.
    """
    pass

# ==============================================================================
# WARNINGS & DEPENDENCIES
# ==============================================================================
# 1. AUTO-LOGOUT: The background task 'check_missed_heartbeats' queries this 
#    DocType every minute. If status is 'Active' but heartbeat is older than
#    3 minutes, the session is forcibly closed.
# ==============================================================================
