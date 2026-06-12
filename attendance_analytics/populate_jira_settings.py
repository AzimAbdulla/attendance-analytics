import frappe

def run():
    frappe.conf.developer_mode = 1
    doc = frappe.get_doc("Jira Integration Settings")
    doc.jira_domain = "https://soxo.atlassian.net"
    doc.jira_user_email = "ashique@soxo.in"
    doc.jira_api_token = "ATATT3xFfGF0uOE5UnreKY-QGHZFIp8YXwKgPZ1BWFxqNnY7HO_JTQV9LOGuSP3fb_HU4rWnSIh_cU9b548OKsnOuSSndHF_DTXaovAn3HZVEIswB5-fGrx_-bkao_iiGNmcvM0hl-Oxp_FIqJZNL2_sdKcR13MeUR-miKJOMUbh3GhxhKjF-0U=0AD466C6"
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    print("Pre-filled Jira Integration Settings with credentials.")

