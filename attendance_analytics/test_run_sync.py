import frappe
from attendance_analytics.jira_sync import extract_adf_text
import requests
from requests.auth import HTTPBasicAuth
from frappe.utils import add_days, nowdate

def run():
    frappe.conf.developer_mode = 1
    settings = frappe.get_doc("Jira Integration Settings")
    
    domain = settings.jira_domain.rstrip('/')
    email = settings.jira_user_email
    token = settings.get_password('jira_api_token')
    
    # We will fetch the last 3 days to ensure we get data, since yesterday might have been empty
    target_date = add_days(nowdate(), -3)
    
    jql = f'worklogDate >= "{target_date}"'
    
    search_url = f"{domain}/rest/api/3/search/jql"
    payload = {
        "jql": jql,
        "fields": ["summary", "issuetype", "priority", "status", "assignee", "reporter"],
        "maxResults": 100
    }
    
    print(f"Searching Jira for issues with worklogs since {target_date}...")
    
    try:
        response = requests.post(search_url, json=payload, auth=HTTPBasicAuth(email, token))
        response.raise_for_status()
        data = response.json()
        issues = data.get("issues", [])
        
        synced_count = 0
        
        print(f"Found {len(issues)} issues with recent worklogs. Processing...")
        
        for issue in issues:
            issue_key = issue.get("key")
            fields = issue.get("fields", {})
            task_title = f"{issue_key}: {fields.get('summary', 'Unknown Task')}"
            priority = fields.get("priority", {}).get("name", "")
            status = fields.get("status", {}).get("name", "")
            
            worklog_url = f"{domain}/rest/api/3/issue/{issue_key}/worklog"
            wl_response = requests.get(worklog_url, auth=HTTPBasicAuth(email, token))
            wl_response.raise_for_status()
            worklogs = wl_response.json().get("worklogs", [])
            
            for wl in worklogs:
                started_date = wl.get("started", "").split("T")[0]
                
                # Only process logs from the target date or later
                if started_date < target_date:
                    continue
                    
                wl_id = wl.get("id")
                unique_name = f"JIRA-{issue_key}-{wl_id}"
                time_spent_hrs = wl.get("timeSpentSeconds", 0) / 3600.0
                
                description = ""
                if "comment" in wl:
                    description = extract_adf_text(wl["comment"]).strip()
                    
                jira_email = wl.get("author", {}).get("emailAddress")
                jira_display_name = wl.get("author", {}).get("displayName", "Unknown")
                
                frappe_employee = None
                
                if jira_email:
                    emp = frappe.get_all("Employee", filters={"user_id": jira_email}, pluck="name", limit=1)
                    if emp: frappe_employee = emp[0]
                        
                if not frappe_employee and jira_display_name != "Unknown":
                    emp = frappe.get_all("Employee", filters={"employee_name": jira_display_name}, pluck="name", limit=1)
                    if emp: frappe_employee = emp[0]
                        
                if not frappe_employee:
                    frappe_employee = settings.default_fallback_employee
                    
                if not frappe_employee:
                    print(f"  [Warning] Could not map Jira user '{jira_display_name}'. Skipping log {wl_id}.")
                    continue
                
                if frappe.db.exists("Worklog", unique_name):
                    doc = frappe.get_doc("Worklog", unique_name)
                    doc.time_spent = time_spent_hrs
                    doc.description = description
                    doc.status = status
                    doc.save(ignore_permissions=True)
                    print(f"  Updated: {unique_name} for {frappe_employee}")
                else:
                    doc = frappe.get_doc({
                        "doctype": "Worklog",
                        "name": unique_name,
                        "date": started_date,
                        "assignee": frappe_employee,
                        "priority": priority,
                        "task": task_title,
                        "description": description,
                        "status": status,
                        "time_spent": time_spent_hrs
                    })
                    doc.insert(ignore_permissions=True)
                    print(f"  Created: {unique_name} for {frappe_employee}")
                    
                synced_count += 1
                
        frappe.db.commit()
        print(f"\nSUCCESS: Synced {synced_count} real worklogs from Jira into Frappe!")
        
    except Exception as e:
        print(f"Failed: {str(e)}")

