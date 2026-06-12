import frappe
import requests
from requests.auth import HTTPBasicAuth
from frappe.utils import nowdate

def extract_adf_text(content_node):
    """Recursively extracts plain text from Jira's Atlassian Document Format (ADF) JSON."""
    text = ""
    if not isinstance(content_node, dict):
        return text
        
    node_type = content_node.get("type")
    
    if node_type == "text":
        text += content_node.get("text", "")
    elif node_type == "hardBreak":
        text += "\n"
    elif node_type == "paragraph":
        for child in content_node.get("content", []):
            text += extract_adf_text(child)
        text += "\n\n"
    elif node_type == "listItem":
        text += "• "
        for child in content_node.get("content", []):
            text += extract_adf_text(child)
    else:
        # Loop through any children
        for child in content_node.get("content", []):
            text += extract_adf_text(child)
            
    return text

def sync_daily_worklogs():
    """
    Cron job triggered at 8 PM.
    Fetches today's worklogs from Jira and maps them to Frappe.
    """
    settings = frappe.get_doc("Jira Integration Settings")
    
    if not settings.enable_sync:
        return
        
    domain = settings.jira_domain.rstrip('/')
    email = settings.jira_user_email
    token = settings.get_password('jira_api_token')
    
    today = nowdate()
    jql = f'worklogDate >= "{today}" AND worklogDate <= "{today}"'
    
    search_url = f"{domain}/rest/api/3/search/jql"
    payload = {
        "jql": jql,
        "fields": ["summary", "issuetype", "priority", "status", "assignee", "reporter"],
        "maxResults": 1000
    }
    
    try:
        # 1. Find all issues worked on today
        response = requests.post(search_url, json=payload, auth=HTTPBasicAuth(email, token))
        response.raise_for_status()
        data = response.json()
        issues = data.get("issues", [])
        
        synced_count = 0
        
        # 2. Process each issue
        for issue in issues:
            issue_key = issue.get("key")
            fields = issue.get("fields", {})
            task_title = f"{issue_key}: {fields.get('summary', 'Unknown Task')}"
            priority = fields.get("priority", {}).get("name", "")
            status = fields.get("status", {}).get("name", "")
            
            # Fetch specific worklogs for this issue
            worklog_url = f"{domain}/rest/api/3/issue/{issue_key}/worklog"
            wl_response = requests.get(worklog_url, auth=HTTPBasicAuth(email, token))
            wl_response.raise_for_status()
            worklogs = wl_response.json().get("worklogs", [])
            
            for wl in worklogs:
                # Jira timestamps look like "2024-08-10T09:00:00.000+0530"
                started_date = wl.get("started", "").split("T")[0]
                
                # Only sync logs that actually belong to 'today' 
                # (since JQL can sometimes pull slightly wider ranges due to timezones)
                if started_date != today:
                    continue
                    
                wl_id = wl.get("id")
                # Create a strict unique ID to prevent duplicates if cron runs twice
                unique_name = f"JIRA-{issue_key}-{wl_id}"
                
                # Convert seconds to hours
                time_spent_hrs = wl.get("timeSpentSeconds", 0) / 3600.0
                
                # Extract clean text description
                description = ""
                if "comment" in wl:
                    description = extract_adf_text(wl["comment"]).strip()
                    
                # --- ROBUST EMPLOYEE MAPPING LOGIC ---
                jira_account_id = wl.get("author", {}).get("accountId")
                jira_display_name = wl.get("author", {}).get("displayName", "Unknown")
                
                frappe_employee = None
                
                # Step 1: Check Mapping Table (100% Bulletproof)
                if jira_account_id:
                    mapping = frappe.get_all("Jira Employee Mapping", filters={"jira_account_id": jira_account_id}, pluck="employee", limit=1)
                    if mapping:
                        frappe_employee = mapping[0]
                        
                # Step 2: Fallback to Fuzzy Name Match (If mapping table isn't filled out yet)
                if not frappe_employee and jira_display_name != "Unknown":
                    emp = frappe.get_all("Employee", filters={"employee_name": jira_display_name}, pluck="name", limit=1)
                    if emp:
                        frappe_employee = emp[0]
                        # Optional: Could auto-create mapping here to save HR time
                        
                # Step 3: Fallback to global setting
                if not frappe_employee:
                    frappe_employee = settings.default_fallback_employee
                    
                # Step 4: Abort if mapping completely failed
                if not frappe_employee:
                    frappe.log_error(message=f"Could not map Jira user '{jira_display_name}' (ID: {jira_account_id}) to Frappe Employee. Skipping worklog {wl_id}.", title="Jira Sync Warning")
                    continue
                
                # Upsert to Frappe Worklog
                if frappe.db.exists("Worklog", unique_name):
                    doc = frappe.get_doc("Worklog", unique_name)
                    doc.time_spent = time_spent_hrs
                    doc.description = description
                    doc.status = status # Update status in case it moved to QA/Done
                    # Do not overwrite assignee if it was manually corrected by HR later
                    doc.save(ignore_permissions=True)
                else:
                    doc = frappe.get_doc({
                        "doctype": "Worklog",
                        "name": unique_name, # Overrides autoname to use our safe Jira ID
                        "date": started_date,
                        "assignee": frappe_employee,
                        "priority": priority,
                        "task": task_title,
                        "description": description,
                        "status": status,
                        "time_spent": time_spent_hrs
                    })
                    doc.insert(ignore_permissions=True)
                    
                synced_count += 1
                
        # Update settings status
        settings.last_sync_status = f"Success: Synced {synced_count} logs on {frappe.utils.now_datetime().strftime('%Y-%m-%d %H:%M')}"
        settings.save(ignore_permissions=True)
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(message=str(e), title="Jira Worklog Sync Failed")
        settings.last_sync_status = f"Failed on {frappe.utils.now_datetime().strftime('%Y-%m-%d %H:%M')}"
        settings.save(ignore_permissions=True)
        frappe.db.commit()
