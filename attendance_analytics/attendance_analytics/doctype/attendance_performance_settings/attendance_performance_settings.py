"""
ATTENDANCE PERFORMANCE SETTINGS
-------------------------------
This is a 'Single' DocType that acts as the global control panel for the app.
Administrators use it to define business rules, penalties, and thresholds.

Logic:
Most of the scoring math happens in the report Python files. Those files 
load this document to decide how many points to deduct for a late arrival, 
an absence, etc.
"""

import frappe
from frappe.model.document import Document

class AttendancePerformanceSettings(Document):
	"""
	Controller for the settings singleton.
	Fields:
	- base_score (float): The initial grade for every employee (e.g., 100.0).
	- office_start_time (time): Standard work start.
	- late_grace_period (int): Minutes allowed after start time without penalty.
	- wfh_status_penalty (float): Points deducted for remote work if discouraged.
	"""
	pass

# ==============================================================================
# WARNINGS & CRITICAL DEPENDENCIES
# ==============================================================================
# 1. SINGLETON: This MUST remain a 'Single' DocType. Reports use 'frappe.get_doc'
#    which expects a unique configuration record.
#
# 2. FIELD NAMES: Do not rename fields in the .json metadata. The Python reports
#    hardcode these fieldnames (e.g. settings.base_score) to access the values.
# ==============================================================================
