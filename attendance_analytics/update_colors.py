import frappe

def run():
    docs = frappe.get_all('Jira Worklog', pluck='name')
    for name in docs:
        doc = frappe.get_doc('Jira Worklog', name)
        doc.save(ignore_permissions=True)
    frappe.db.commit()
    print("Colors updated successfully")
