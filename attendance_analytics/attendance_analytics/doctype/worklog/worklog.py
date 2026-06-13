"""
WORKLOG DOCTYPE CONTROLLER
--------------------------
Handles server-side logic for individual worklog entries.
Includes automated card coloring for the Kanban view.
"""

from frappe.model.document import Document

class Worklog(Document):
    def before_save(self):
        """
        Triggered before every database save.
        Ensures the 'color' field is updated based on status/priority.
        """
        self.set_color()
        
    def set_color(self):
        """
        Assigns a hex color code to the document. 
        This is natively picked up by Frappe Kanban boards for card indicators.
        """
        # status_colors (dict): Color mapping for different workflow stages.
        status_colors = {
            "Done": "#2ecc71",               # Green
            "QA Verified": "#2ecc71",
            "Staging QA Verified": "#2ecc71",
            "UAT QA Verified": "#2ecc71",
            "Ready": "#2ecc71",
            "Open": "#e74c3c",               # Red
            "Backlog": "#e74c3c",
            "For Discussion": "#e74c3c",
            "QA Rejected": "#e74c3c",
            "Staging QA Rejected": "#e74c3c",
            "UAT QA Rejected": "#e74c3c",
            "Dev Progress": "#f39c12",       # Orange
            "QA Progress": "#f39c12",
            "Code Review": "#f39c12",
            "QA Ready": "#f39c12",
            "QA Pending": "#f39c12",
            "UAT QA Pending": "#f39c12",
            "UAT QA Ready": "#f39c12"
        }
        
        # priority_colors (dict): Fallback if status is not defined.
        priority_colors = {
            "Highest": "#ff0000",
            "High": "#ff8c00",
            "Medium": "#f1c40f",
            "Low": "#3498db",
            "Lowest": "#2ecc71"
        }
        
        # LOGIC: Prioritize status color, fallback to priority color.
        if self.status and self.status in status_colors:
            self.color = status_colors[self.status]
        elif self.priority and self.priority in priority_colors:
            self.color = priority_colors[self.priority]
        else:
            self.color = "#bdc3c7" # Grey default
