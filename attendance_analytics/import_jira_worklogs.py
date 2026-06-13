"""
JIRA SAMPLE DATA IMPORTER
-------------------------
A utility script used to bootstrap the system with historical data from
the 'Jira Worklogs Report' Excel file.

Logic:
1. Re-creates the 'Worklog' DocType if missing.
2. Parses the Excel file using 'openpyxl'.
3. Correctly identifies Squads and Assignees from header rows.
4. Corrects time formatting and inserts records into the database.
"""

import frappe
import openpyxl

def run():
    """
    Main importer execution.
    - Clears existing worklogs.
    - Loops through Excel rows and maps columns to Frappe fields.
    """
    frappe.conf.developer_mode = 1
    doctype_name = "Worklog"

    # 1. Start fresh with data
    print("Clearing old data...")
    if frappe.db.exists("DocType", doctype_name):
        frappe.db.delete(doctype_name)
        frappe.db.commit()
    
    # 2. Ensure DocType exists with the standard simplified structure
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
            {"fieldname": "assignee", "label": "Assignee", "fieldtype": "Link", "options": "Employee", "in_list_view": 1, "in_standard_filter": 1},
            {"fieldname": "priority", "label": "Priority", "fieldtype": "Select", "options": "\nHighest\nHigh\nMedium\nLow\nLowest", "in_list_view": 1, "in_standard_filter": 1},
            {"fieldname": "task", "label": "Task", "fieldtype": "Text", "in_list_view": 1, "reqd": 1},
            {"fieldname": "description", "label": "Description", "fieldtype": "Text Editor"},
            {"fieldname": "status", "label": "Status", "fieldtype": "Data", "in_list_view": 1, "in_standard_filter": 1},
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

    # 3. Import Sample Data from Excel
    print("Importing Excel data...")
    file_path = '/home/azim/frappe-bench/Jira_Worklogs_Report_2026-05-16 (1).xlsx'
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))
    
    count = 0
    current_assignee = ""

    for row in rows[1:]:  # skip header row
        # Identify group headers (Rows without a serial number)
        if len(row) > 1 and not row[0]:
            text = str(row[1] or "").strip()
            # Group headers often contain the person's name before their total hours
            if text and not text.startswith("SQUAD-"):
                current_assignee = text.split(" (")[0]
        
        # Valid data row (Starts with a number)
        elif len(row) > 0 and isinstance(row[0], int):
            try:
                # Prefer explicit assignee column, fallback to the group header name
                assignee_val = str(row[9]).strip() if row[9] else current_assignee

                doc = frappe.get_doc({
                    "doctype": doctype_name,
                    "date": frappe.utils.nowdate(),
                    "assignee": assignee_val,
                    "priority": str(row[2]) if row[2] else "",
                    "task": str(row[3]) if row[3] else "Unknown Task",
                    "status": str(row[4]) if row[4] else "",
                    # row[13] contains the 'Time Spent' float
                    "time_spent": float(row[13]) if row[13] else 0.0,
                })
                doc.insert(ignore_permissions=True)
                count += 1
            except Exception as e:
                print(f"Error importing row {row[0]}: {e}")
                
    frappe.db.commit()
    print(f"Successfully imported {count} simplified Worklogs.")
