import frappe
import openpyxl

def run():
    frappe.conf.developer_mode = 1
    doctype_name = "Worklog"

    # 1. Start fresh with data
    print("Clearing old data...")
    frappe.db.delete(doctype_name)
    frappe.db.commit()
    
    # 2. Ensure DocType exists with improved structure
    if not frappe.db.exists("DocType", doctype_name):
        print("Creating simplified DocType...")
        doc = frappe.get_doc({
        "doctype": "DocType",
        "name": doctype_name,
        "module": "Attendance Analytics",
        "custom": 0,
        "autoname": "format:WL-{YYYY}-{MM}-{####}",
        "fields": [
            {"fieldname": "date", "label": "Date", "fieldtype": "Date", "in_list_view": 1, "in_standard_filter": 1, "reqd": 1, "default": "Today"},
            {"fieldname": "assignee", "label": "Assignee", "fieldtype": "Data", "in_list_view": 1, "in_standard_filter": 1, "default": frappe.session.user},
            {"fieldname": "priority", "label": "Priority", "fieldtype": "Select", "options": "\nHighest\nHigh\nMedium\nLow\nLowest", "in_list_view": 1, "in_standard_filter": 1},
            {"fieldname": "task", "label": "Task", "fieldtype": "Text", "in_list_view": 1, "reqd": 1},
            {"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "\nBacklog\nOpen\nFor Discussion\nDev Progress\nCode Review\nReady\nQA Ready\nQA Pending\nQA Progress\nQA Rejected\nQA Verified\nStaging QA Rejected\nStaging QA Verified\nUAT QA Ready\nUAT QA Pending\nUAT QA Rejected\nUAT QA Verified\nDone", "in_list_view": 1, "in_standard_filter": 1},
            {"fieldname": "time_spent", "label": "Time Spent (hrs)", "fieldtype": "Float", "in_list_view": 1},
            {"fieldname": "color", "label": "Color", "fieldtype": "Color", "hidden": 1},
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "HR Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "Employee", "read": 1, "write": 1, "create": 1}
        ],
        "title_field": "task",
        "sort_field": "modified",
        "sort_order": "DESC"
    })
        doc.insert(ignore_permissions=True)
    frappe.db.commit()

    # 3. Import Sample Data mapping only the requested columns
    print("Importing Excel data...")
    file_path = '/home/azim/frappe-bench/Jira_Worklogs_Report_2026-05-16 (1).xlsx'
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))
    
    count = 0
    current_assignee = ""

    for row in rows[1:]:  # skip header
        # Identify group headers to extract Assignee Name
        if len(row) > 1 and not row[0]:
            text = str(row[1] or "").strip()
            if text and not text.startswith("SQUAD-"):
                current_assignee = text.split(" (")[0]
        
        # Valid data row
        elif len(row) > 0 and isinstance(row[0], int):
            try:
                assignee_val = str(row[9]).strip() if row[9] else current_assignee

                doc = frappe.get_doc({
                    "doctype": doctype_name,
                    "date": frappe.utils.nowdate(),
                    "assignee": assignee_val,
                    "priority": str(row[2]) if row[2] else "",
                    "task": str(row[3]) if row[3] else "Unknown Task",
                    "status": str(row[4]) if row[4] else "",
                    "time_spent": float(row[13]) if row[13] else 0.0,
                })
                doc.insert(ignore_permissions=True)
                count += 1
            except Exception as e:
                print(f"Error importing row {row[0]}: {e}")
                
    frappe.db.commit()
    print(f"Successfully imported {count} simplified Worklogs.")
