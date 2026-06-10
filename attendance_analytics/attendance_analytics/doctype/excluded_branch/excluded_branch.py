"""
EXCLUDED BRANCH
---------------
Child DocType linked to 'Attendance Performance Settings'.
Allows HR to list specific physical locations to be ignored by analytics.
"""

import frappe
from frappe.model.document import Document

class ExcludedBranch(Document):
	"""
	Variables:
	- branch (link): Reference to the 'Branch' DocType.
	"""
	pass
