"""
JIRA WORKLOG SYNCHRONIZATION ENGINE
-----------------------------------
This script is the core automation for pulling data from the Jira API into Frappe.
It is designed to run daily at 8 PM via a Frappe Cron Job.

Key Logic:
1. Authenticates using credentials stored in site_config.json (Environment).
2. Performs a JQL search for all issues with worklogs on the current date.
3. Iterates through each issue and fetches individual time-entry details.
4. Maps Jira users to Frappe Employees using the 'Jira Employee Mapping' table.
5. Parses complex Atlassian Document Format (ADF) comments into clean text.
"""

import frappe
import requests
from requests.auth import HTTPBasicAuth
from frappe.utils import nowdate

def extract_adf_text(content_node):
    """
    Recursively extracts plain text from Jira's Atlassian Document Format (ADF).
    
    Arguments:
        content_node (dict): A nested JSON node from Jira's comment object.
        
    Returns:
        text (str): Cleaned, human-readable text string.
    """
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
        text += "• " # Convert Jira list items to standard bullet points
        for child in content_node.get("content", []):
            text += extract_adf_text(child)
    else:
        # Generic recursion for unknown node types (ordered lists, etc.)
        for child in content_node.get("content", []):
            text += extract_adf_text(child)
            
    return text

def sync_daily_worklogs():
    """
    Main Cron function. Orchestrates the 8 PM daily fetch.
    
    Variables:
        domain (str): Jira base URL (e.g. https://soxo.atlassian.net).
        email (str): Username for API authentication.
        token (str): Encrypted API token retrieved from Settings.
        today (str): Current date in YYYY-MM-DD format.
    """
    settings = frappe.get_doc("Jira Integration Settings")
    
    # Skip if the user has manually disabled the sync in settings
    if not settings.enable_sync:
        return
        
    # FETCH CREDENTIALS FROM ENVIRONMENT (site_config.json)
    domain = (frappe.conf.jira_domain or "").rstrip('/')
    email = frappe.conf.jira_user_email
    token = frappe.conf.jira_api_token
    
    if not all([domain, email, token]):
        frappe.log_error(message="Jira credentials missing in site_config.json. Sync aborted.", title="Jira Sync Error")
        settings.last_sync_status = "Failed: Missing API Credentials in environment."
        settings.save(ignore_permissions=True)
        return

    today = nowdate()
    
    # JQL: Searches specifically for issues updated today to reduce API load
    jql = f'worklogDate >= "{today}" AND worklogDate <= "{today}"'
    
    search_url = f"{domain}/rest/api/3/search/jql"
    payload = {
        "jql": jql,
        "fields": ["summary", "issuetype", "priority", "status", "assignee", "reporter"],
        "maxResults": 1000
    }
    
    try:
        # STEP 1: Identify all issues with activity
        response = requests.post(search_url, json=payload, auth=HTTPBasicAuth(email, token))
        response.raise_for_status()
        data = response.json()
        issues = data.get("issues", [])
        
        synced_count = 0
        
        # STEP 2: Process individual worklogs for each issue
        for issue in issues:
            issue_key = issue.get("key") # e.g. SOXO-123
            fields = issue.get("fields", {})
            task_title = f"{issue_key}: {fields.get('summary', 'Unknown Task')}"
            priority = fields.get("priority", {}).get("name", "")
            status = fields.get("status", {}).get("name", "")
            
            # Fetch the actual time-log entries for this specific ticket
            worklog_url = f"{domain}/rest/api/3/issue/{issue_key}/worklog"
            wl_response = requests.get(worklog_url, auth=HTTPBasicAuth(email, token))
            wl_response.raise_for_status()
            worklogs = wl_response.json().get("worklogs", [])
            
            for wl in worklogs:
                # Jira 'started' format: "2024-08-10T09:00:00.000+0530"
                started_date = wl.get("started", "").split("T")[0]
                
                # Filter to only 'today' to avoid redundant past syncing
                if started_date != today:
                    continue
                    
                wl_id = wl.get("id")
                # unique_name (str): Strict unique key to prevent database duplicates
                unique_name = f"JIRA-{issue_key}-{wl_id}"
                
                # time_spent_hrs (float): Converts seconds to decimal hours (e.g. 1.5)
                time_spent_hrs = wl.get("timeSpentSeconds", 0) / 3600.0
                
                description = ""
                if "comment" in wl:
                    description = extract_adf_text(wl["comment"]).strip()
                    
                # --- EMPLOYEE MAPPING LOGIC ---
                jira_account_id = wl.get("author", {}).get("accountId")
                jira_display_name = wl.get("author", {}).get("displayName", "Unknown")
                
                frappe_employee = None
                
                # Priority 1: Exact Account ID match (Unbreakable)
                if jira_account_id:
                    mapping = frappe.get_all("Jira Employee Mapping", filters={"jira_account_id": jira_account_id}, pluck="employee", limit=1)
                    if mapping:
                        frappe_employee = mapping[0]
                        
                # Priority 2: Exact Name match (Fallback)
                if not frappe_employee and jira_display_name != "Unknown":
                    emp = frappe.get_all("Employee", filters={"employee_name": jira_display_name}, pluck="name", limit=1)
                    if emp:
                        frappe_employee = emp[0]
                        
                # Priority 3: Global Fallback Setting (Safety net)
                if not frappe_employee:
                    frappe_employee = settings.default_fallback_employee
                    
                if not frappe_employee:
                    # Log error if no mapping is possible
                    frappe.log_error(message=f"Jira user '{jira_display_name}' could not be mapped to any Frappe Employee. Log skipped.", title="Jira Sync Warning")
                    continue
                
                # SAVE DATA TO FRAPPE
                if frappe.db.exists("Worklog", unique_name):
                    # Update existing record
                    doc = frappe.get_doc("Worklog", unique_name)
                    doc.time_spent = time_spent_hrs
                    doc.description = description
                    doc.status = status 
                    doc.save(ignore_permissions=True)
                else:
                    # Create new record
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
                    
                synced_count += 1
                
        # Final Status Update
        settings.last_sync_status = f"Success: {synced_count} logs synced at {frappe.utils.now_datetime()}"
        settings.save(ignore_permissions=True)
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(message=str(e), title="Jira Worklog Sync Crash")
        settings.last_sync_status = f"Failed: {str(e)}"
        settings.save(ignore_permissions=True)
        frappe.db.commit()

# ==============================================================================
# WARNINGS & DEPENDENCIES
# ==============================================================================
# 1. API LIMITS: This script uses a 1000 maxResults limit. Large organizations
#    with thousands of logs per day may need to implement pagination.
#
# 2. PRIVACY: If Jira emails are hidden, the 'accountId' mapping is the ONLY
#    bulletproof way to link employees. Ensure 'Jira Employee Mapping' is 
#    filled for every user.
# ==============================================================================
