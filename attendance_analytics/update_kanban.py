import frappe

def run():
    boards = frappe.get_all('Kanban Board', filters={'reference_doctype': 'Jira Worklog'})
    for board in boards:
        # Kanban Board doc has a field 'kanban_board_fields' (JSON string) or relies on DocType title_field
        # We'll explicitly set the Title Field in the DocType metadata programmatically so it doesn't touch the JSON file on disk,
        # but actually, frappe.custom_doc is better, or we can just set it in Property Setter.
        
        # The safest way without touching DocType JSON is Property Setter
        frappe.make_property_setter({
            'doctype': 'Jira Worklog',
            'doctype_or_field': 'DocType',
            'property': 'title_field',
            'value': 'task',
            'property_type': 'Data'
        })
    frappe.db.commit()
    print("Updated Property Setter for Kanban Board title")
