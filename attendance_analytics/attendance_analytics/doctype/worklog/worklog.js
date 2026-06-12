
frappe.ui.form.on("Worklog", {
	refresh: function(frm) {
		// Auto-fill for new records
		if (frm.is_new()) {
			if (!frm.doc.date) frm.set_value("date", frappe.datetime.nowdate());
			if (!frm.doc.assignee) {
				frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name", (r) => {
					if (r && r.name) {
						frm.set_value("assignee", r.name);
					}
				});
			}
		}

		// Permissions check: Lock fields for standard Employees
		const is_manager = frappe.user_roles.includes("System Manager") || frappe.user_roles.includes("HR Manager");
		
		if (!is_manager) {
			frm.set_df_property("date", "read_only", 1);
			frm.set_df_property("assignee", "read_only", 1);
		}
	}
});
