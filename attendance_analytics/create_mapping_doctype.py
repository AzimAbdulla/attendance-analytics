import frappe

def run():
    frappe.conf.developer_mode = 1
    doctype_name = "Jira Employee Mapping"

    if frappe.db.exists("DocType", doctype_name):
        print(f"DocType {doctype_name} already exists.")
        return

    doc = frappe.get_doc({
        "doctype": "DocType",
        "name": doctype_name,
        "module": "Attendance Analytics",
        "custom": 0,
        "autoname": "field:employee",
        "fields": [
            {"fieldname": "employee", "label": "Employee", "fieldtype": "Link", "options": "Employee", "in_list_view": 1, "reqd": 1, "unique": 1},
            {"fieldname": "jira_account_id", "label": "Jira Account ID", "fieldtype": "Data", "in_list_view": 1, "reqd": 1, "unique": 1, "description": "The unique accountId string from Jira (e.g., 712020:410ac...)"},
            {"fieldname": "jira_display_name", "label": "Jira Display Name (Reference)", "fieldtype": "Data", "in_list_view": 1, "description": "Optional: For easy reading only, script uses Account ID"}
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "HR Manager", "read": 1, "write": 1, "create": 1, "delete": 1}
        ],
        "title_field": "jira_display_name",
        "search_fields": "employee, jira_account_id"
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"Successfully created {doctype_name} DocType.")
