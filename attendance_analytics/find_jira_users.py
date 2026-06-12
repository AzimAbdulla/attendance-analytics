import frappe
import requests
from requests.auth import HTTPBasicAuth
from frappe.utils import add_days, nowdate

def run():
    frappe.conf.developer_mode = 1
    settings = frappe.get_doc("Jira Integration Settings")
    
    domain = settings.jira_domain.rstrip('/')
    email = settings.jira_user_email
    token = settings.get_password('jira_api_token')
    
    target_date = add_days(nowdate(), -7) # Check last 7 days to get a good list of users
    jql = f'worklogDate >= "{target_date}"'
    
    search_url = f"{domain}/rest/api/3/search/jql"
    payload = {
        "jql": jql,
        "fields": ["summary", "assignee", "reporter"],
        "maxResults": 100
    }
    
    try:
        response = requests.post(search_url, json=payload, auth=HTTPBasicAuth(email, token))
        response.raise_for_status()
        issues = response.json().get("issues", [])
        
        unique_users = {} # {account_id: display_name}
        
        for issue in issues:
            issue_key = issue.get("key")
            worklog_url = f"{domain}/rest/api/3/issue/{issue_key}/worklog"
            wl_response = requests.get(worklog_url, auth=HTTPBasicAuth(email, token))
            worklogs = wl_response.json().get("worklogs", [])
            
            for wl in worklogs:
                author = wl.get("author", {})
                acc_id = author.get("accountId")
                d_name = author.get("displayName", "Unknown")
                if acc_id:
                    unique_users[acc_id] = d_name
                    
        print("\n--- JIRA USERS FOUND ---")
        unmapped = []
        for acc_id, d_name in unique_users.items():
            # Check if already mapped
            if frappe.db.exists("Jira Employee Mapping", {"jira_account_id": acc_id}):
                continue
                
            # Try to fuzzy match to Frappe Employee
            emp = frappe.get_all("Employee", filters={"employee_name": d_name}, pluck="name", limit=1)
            if emp:
                # Auto-create mapping
                doc = frappe.get_doc({
                    "doctype": "Jira Employee Mapping",
                    "employee": emp[0],
                    "jira_account_id": acc_id,
                    "jira_display_name": d_name
                })
                doc.insert(ignore_permissions=True)
                print(f"Auto-mapped: {d_name} -> {emp[0]}")
            else:
                unmapped.append((d_name, acc_id))
                
        frappe.db.commit()
        
        if unmapped:
            print("\n--- UNMAPPED USERS (Need manual linking) ---")
            for name, acc_id in unmapped:
                print(f"Name: {name} | Account ID: {acc_id}")
                
    except Exception as e:
        print(f"Error: {str(e)}")

