"""
JIRA EMPLOYEE MAPPING
---------------------
This table provides the 1:1 link between a Jira user and a Frappe employee.
It is required because Jira often hides email addresses from its API.
"""

from frappe.model.document import Document

class JiraEmployeeMapping(Document):
    """
    Fields:
    - employee (link): The official Frappe Employee ID.
    - jira_account_id (data): The unique, immutable accountId from Jira.
    - jira_display_name (data): Reference name for easier manual auditing.
    """
    pass

# ==============================================================================
# WARNINGS & DEPENDENCIES
# ==============================================================================
# 1. UNIQUENESS: Both 'employee' and 'jira_account_id' are marked as Unique.
#    One Jira user cannot be mapped to two Frappe employees.
#
# 2. SYNC RELIANCE: The 'jira_sync.py' engine looks up this table by 
#    'jira_account_id' first. If mapping is missing, the log may be 
#    assigned to a fallback user.
# ==============================================================================
