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
    
    target_date = add_days(nowdate(), -60) # Look back 60 days to catch infrequent loggers
    jql = f'worklogDate >= "{target_date}"'
    
    search_url = f"{domain}/rest/api/3/search/jql"
    payload = {
        "jql": jql,
        "fields": ["summary"],
        "maxResults": 200
    }
    
    print(f"Deep search in Jira for worklogs since {target_date}...")
    
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
                    
        unmapped = []
        for acc_id, d_name in unique_users.items():
            if not frappe.db.exists("Jira Employee Mapping", {"jira_account_id": acc_id}):
                unmapped.append((d_name, acc_id))
                
        if unmapped:
            print("\n--- STILL UNMAPPED USERS (Found in last 60 days) ---")
            for name, acc_id in unmapped:
                print(f"Name: {name} | Account ID: {acc_id}")
        else:
            print("\nAwesome! Every single person who has logged time in the last 60 days is perfectly mapped in Frappe.")
                
    except Exception as e:
        print(f"Error: {str(e)}")

