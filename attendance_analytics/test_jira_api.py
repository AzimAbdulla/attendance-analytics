import frappe
import requests
from requests.auth import HTTPBasicAuth
from frappe.utils import nowdate
import json

def run():
    frappe.conf.developer_mode = 1
    settings = frappe.get_doc("Jira Integration Settings")
    
    domain = settings.jira_domain.rstrip('/')
    email = settings.jira_user_email
    token = settings.get_password('jira_api_token')
    
    # Try to fetch recent issues to find one with a comment in the worklog
    jql = f'worklogDate >= "-30d"'
    
    search_url = f"{domain}/rest/api/3/search/jql"
    payload = {
        "jql": jql,
        "fields": ["summary", "issuetype", "priority", "status", "assignee", "reporter"],
        "maxResults": 10
    }
    
    print(f"Searching Jira for issues with worklogs...")
    try:
        response = requests.post(search_url, json=payload, auth=HTTPBasicAuth(email, token))
        response.raise_for_status()
        data = response.json()
        
        issues = data.get("issues", [])
        if not issues:
            print("No issues found.")
            return
            
        for issue in issues:
            issue_key = issue.get("key")
            worklog_url = f"{domain}/rest/api/3/issue/{issue_key}/worklog"
            wl_response = requests.get(worklog_url, auth=HTTPBasicAuth(email, token))
            wl_response.raise_for_status()
            wl_data = wl_response.json()
            
            worklogs = wl_data.get("worklogs", [])
            for wl in worklogs:
                if "comment" in wl:
                    print(f"\n--- Found Issue: {issue_key} with a Comment! ---")
                    print(json.dumps(wl.get("comment"), indent=2))
                    return
                    
        print("No worklogs with comments found in the recent sample.")
            
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        if e.response is not None:
            print(e.response.text)

