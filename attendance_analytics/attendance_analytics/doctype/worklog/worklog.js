/**
 * WORKLOG CLIENT SCRIPT
 * ---------------------
 * Manages the User Interface behavior for the Worklog form.
 * 
 * Features:
 * 1. Auto-fills current user and date for new entries.
 * 2. Enforces read-only lockdown for standard employees to prevent falsifying logs.
 */

frappe.ui.form.on("Worklog", {
	refresh: function(frm) {
		// --- AUTO-FILL LOGIC ---
		// Only applies to brand new documents that haven't been saved yet.
		if (frm.is_new()) {
			// date (str): Defaults to current server date.
			if (!frm.doc.date) frm.set_value("date", frappe.datetime.nowdate());
			
			// assignee (Link): Fetches the official Employee ID linked to the user.
			if (!frm.doc.assignee) {
				frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name", (r) => {
					if (r && r.name) {
						frm.set_value("assignee", r.name);
					}
				});
			}
		}

		// --- PERMISSION LOCKDOWN ---
		// Identifies if the user has management privileges.
		const is_manager = frappe.user_roles.includes("System Manager") || frappe.user_roles.includes("HR Manager");
		
		// If the user is a standard Employee, they cannot edit the Date or Assignee.
		// This prevents employees from logging work for other people or back-dating entries.
		if (!is_manager) {
			frm.set_df_property("date", "read_only", 1);
			frm.set_df_property("assignee", "read_only", 1);
		}
	}
});
