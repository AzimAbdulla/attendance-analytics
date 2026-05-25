// Copyright (c) 2026, Azim Abdulla and contributors
// For license information, please see license.txt

frappe.query_reports["Daily Work Duration Report"] = {
	"filters": [
		{
			"fieldname": "date",
			"label": __("Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.nowdate(),
			"reqd": 1
		},
		{
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options": "Department"
		},
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee"
		}
	],
	"get_datatable_options": function(options) {
		options.showRowIndex = false;
		options.serialNoColumn = false;
		options.layout = "fluid";

		if (options.columns) {
			options.columns[0].fixed = true; // Employee ID
			options.columns[1].fixed = true; // Employee Name
		}

		return options;
	}
};
