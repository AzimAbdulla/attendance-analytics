"""
APP HOOKS: ATTENDANCE ANALYTICS
-------------------------------
Defines the integration points between this app and the Frappe framework.
Registers custom fixtures and background task schedules.
"""

# fixtures (list): DocTypes whose data should be exported as JSON for deployment.
# We include 'Attendance Performance Settings' so penalties don't need manual setup.
fixtures = [
    {"doctype": "Attendance Performance Settings"},
    {"doctype": "Workspace", "filters": [["name", "in", ["HR"]]]}
]

app_name = "attendance_analytics"
app_title = "Attendance Analytics"
app_publisher = "Contributors"
app_description = "Attendance trend analytics and reporting"
app_email = "team@example.com"
app_license = "mit"

# ==============================================================================
# WARNINGS & CRITICAL DEPENDENCIES
# ==============================================================================
# 1. EXPORT-FIXTURES: Running 'bench export-fixtures' will overwrite the JSON
#    files in the 'fixtures/' directory. 
#
# 2. APP NAME: If the app name is changed, all import statements in the 
#    Python controllers will fail.
# ==============================================================================
