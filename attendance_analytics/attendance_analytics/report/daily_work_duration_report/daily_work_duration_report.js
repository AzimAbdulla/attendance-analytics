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
			options.columns[0].fixed = true; // Employee Name (linked)
		}

		const original_formatter = options.formatter;
		options.formatter = (value, row, column, data) => {
			if (column.id === 'employee' && data && data.employee_name) {
				return `<a class="grey" href="/app/employee/${value}">${data.employee_name}</a>`;
			}
			if (original_formatter) {
				return original_formatter(value, row, column, data);
			}
			return value;
		};

		return options;
	}
};
