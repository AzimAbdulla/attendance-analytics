"""
JIRA INTEGRATION SETTINGS
-------------------------
A Single DocType that acts as the control panel for the Jira API Sync.
Note: Sensitive credentials (Domain, Token) have been moved to site_config.json
for enhanced security. This DocType now only manages the sync toggle and status.
"""

from frappe.model.document import Document

class JiraIntegrationSettings(Document):
    """
    Fields:
    - enable_sync (check): Global toggle to turn the 8 AM cron job on/off.
    - last_sync_status (data): Read-only indicator of the last sync result.
    - default_fallback_employee (link): Used if mapping fails during sync.
    """
    pass

# ==============================================================================
# WARNINGS & DEPENDENCIES
# ==============================================================================
# 1. ENVIRONMENT VARIABLES: The sync engine looks for 'jira_domain', 
#    'jira_user_email', and 'jira_api_token' inside 'frappe.conf'. 
#    The sync will fail if these are not set via 'bench set-config'.
#
# 2. SINGLETON: This must remain a Single DocType.
# ==============================================================================
