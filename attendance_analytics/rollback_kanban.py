import frappe

def run():
    frappe.db.delete("Property Setter", {
        "doc_type": "Jira Worklog",
        "property": "title_field"
    })
    frappe.db.commit()
    print("Property Setter rolled back")
