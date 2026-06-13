"""
JIRA INTEGRATION SETTINGS
-------------------------
A Single DocType that acts as the control panel for the Jira API Sync.
Stores credentials securely using encrypted Password fields.
"""

from frappe.model.document import Document

class JiraIntegrationSettings(Document):
    """
    Fields:
    - jira_domain (data): The base URL of your Atlassian instance.
    - jira_user_email (data): The email used to generate the API Token.
    - jira_api_token (password): The secret token (hidden/encrypted).
    - enable_sync (check): Global toggle to turn the 8 PM cron job on/off.
    - default_fallback_employee (link): Used if mapping fails during sync.
    """
    pass

# ==============================================================================
# WARNINGS & DEPENDENCIES
# ==============================================================================
# 1. ENCRYPTION: The API token is stored as a 'Password' type. It can only 
#    be retrieved in Python using 'self.get_password()'.
#
# 2. SINGLETON: This must remain a Single DocType. The 'jira_sync.py' script
#    hardcodes 'frappe.get_doc("Jira Integration Settings")'.
# ==============================================================================
