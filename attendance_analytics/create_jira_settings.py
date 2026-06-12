import frappe

def run():
    frappe.conf.developer_mode = 1
    doctype_name = "Jira Integration Settings"

    if frappe.db.exists("DocType", doctype_name):
        print(f"DocType {doctype_name} already exists.")
        return

    doc = frappe.get_doc({
        "doctype": "DocType",
        "name": doctype_name,
        "module": "Attendance Analytics",
        "custom": 0,
        "issingle": 1,
        "fields": [
            {"fieldname": "enable_sync", "label": "Enable Daily Sync (8 PM)", "fieldtype": "Check", "default": "1"},
            {"fieldname": "cb_1", "fieldtype": "Column Break"},
            {"fieldname": "last_sync_status", "label": "Last Sync Status", "fieldtype": "Data", "read_only": 1},
            
            {"fieldname": "sb_credentials", "label": "Jira API Credentials", "fieldtype": "Section Break"},
            {"fieldname": "jira_domain", "label": "Jira Base URL", "fieldtype": "Data", "reqd": 1, "description": "e.g., https://soxo.atlassian.net"},
            {"fieldname": "jira_user_email", "label": "Jira User Email", "fieldtype": "Data", "reqd": 1, "description": "Email address of the token owner."},
            {"fieldname": "jira_api_token", "label": "API Token", "fieldtype": "Password", "reqd": 1, "description": "Generated from Atlassian Security page."},
            
            {"fieldname": "sb_mapping", "label": "Advanced Settings", "fieldtype": "Section Break", "collapsible": 1},
            {"fieldname": "default_fallback_employee", "label": "Fallback Employee", "fieldtype": "Link", "options": "Employee", "description": "If Jira assignee cannot be matched to a Frappe Employee, log the task to this user instead."},
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 0}
        ]
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"Successfully created {doctype_name} DocType.")

