"""
EXCLUDED EMPLOYMENT TYPE
------------------------
Child DocType linked to 'Attendance Performance Settings'.
Used to hide categories like 'Intern' or 'Freelancer' from performance rankings.
"""

import frappe
from frappe.model.document import Document

class ExcludedEmploymentType(Document):
	"""
	Variables:
	- employment_type (link): Reference to 'Employment Type' DocType.
	"""
	pass
