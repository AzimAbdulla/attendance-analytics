
frappe.ui.form.on("Worklog", {
	refresh: function(frm) {
		// Auto-fill for new records
		if (frm.is_new()) {
			if (!frm.doc.date) frm.set_value("date", frappe.datetime.nowdate());
			if (!frm.doc.assignee || frm.doc.assignee === "Administrator") frm.set_value("assignee", frappe.session.user_fullname);
		}

		// Permissions check: Lock fields for standard Employees
		const is_manager = frappe.user_roles.includes("System Manager") || frappe.user_roles.includes("HR Manager");
		
		if (!is_manager) {
			frm.set_df_property("date", "read_only", 1);
			frm.set_df_property("assignee", "read_only", 1);
		}
	}
});
