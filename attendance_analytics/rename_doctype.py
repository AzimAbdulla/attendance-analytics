import frappe
def run():
    if frappe.db.exists("DocType", "Jira Worklog"):
        frappe.rename_doc("DocType", "Jira Worklog", "Worklog", force=True)
        frappe.db.commit()
        print("DocType renamed from 'Jira Worklog' to 'Worklog'")
    else:
        print("DocType 'Jira Worklog' not found")
