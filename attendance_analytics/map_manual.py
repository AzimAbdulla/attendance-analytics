import frappe

def run():
    mappings = [
        {"jira_name": "Rufsal", "account_id": "712020:e494a8c1-b6dc-4798-8a89-43c9cea1a06b", "frappe_name": "Rufsal N K"},
        {"jira_name": "Aiswarya Ek", "account_id": "712020:c8e91070-469e-4382-ac5b-0a3c111543ab", "frappe_name": "Aiswarya E K"},
        {"jira_name": "Shifana", "account_id": "712020:03af5a61-7f08-44f3-bc9d-a97fdd087414", "frappe_name": "Fathima Shifana"},
        {"jira_name": "anagha", "account_id": "712020:74b49313-9a3a-4060-956c-4c231b3fa1d6", "frappe_name": "Anagha P K"},
        {"jira_name": "NihalaDilshi", "account_id": "712020:a8ea6453-e364-4034-8823-74d3f48c4616", "frappe_name": "Nihala Dilshi C M"},
        {"jira_name": "Jinishak", "account_id": "712020:28fafd00-bc88-4681-be89-441a0cc2ac65", "frappe_name": "Jinisha K"},
        {"jira_name": "Masood", "account_id": "712020:3872e756-b25a-4480-b98a-85985e07a33b", "frappe_name": "Masood Abdul Samad"},
        {"jira_name": "shakkir", "account_id": "712020:578d6f8c-04f0-44fe-8dd5-b5f33515cadb", "frappe_name": "Shakkir Ahammad"}
    ]
    
    frappe.conf.developer_mode = 1
    
    for m in mappings:
        emp = frappe.get_all("Employee", filters={"employee_name": ["like", f"%{m['frappe_name']}%"]}, pluck="name", limit=1)
        if emp:
            emp_id = emp[0]
            if not frappe.db.exists("Jira Employee Mapping", {"jira_account_id": m['account_id']}):
                doc = frappe.get_doc({
                    "doctype": "Jira Employee Mapping",
                    "employee": emp_id,
                    "jira_account_id": m['account_id'],
                    "jira_display_name": m['jira_name']
                })
                doc.insert(ignore_permissions=True)
                print(f"Mapped: {m['jira_name']} -> {emp_id} ({m['frappe_name']})")
            else:
                print(f"Already Mapped: {m['jira_name']}")
        else:
            print(f"ERROR: Could not find Frappe Employee for '{m['frappe_name']}'")
            
    frappe.db.commit()
