// Copyright (c) 2026, Azim Abdulla and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly Work Duration Report"] = {
	"filters": [
		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Select",
			"options": "January\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
			"reqd": 1
		},
		{
			"fieldname": "year",
			"label": __("Year"),
			"fieldtype": "Select",
			"options": "2024\n2025\n2026\n2027",
			"reqd": 1
		},
		{
			"fieldname": "employee",
			"label": __("Employee Name"),
			"fieldtype": "Data",
			"reqd": 1
		}
	],
	"onload": function(report) {
		const url_params = frappe.utils.get_query_params();
		
		let default_month = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"][frappe.datetime.str_to_obj(frappe.datetime.nowdate()).getMonth()];
		let default_year = frappe.datetime.str_to_obj(frappe.datetime.nowdate()).getFullYear();

		let month = url_params.month || default_month;
		let year = url_params.year || default_year;

		// Small timeout ensures Frappe initializes filter controls before we set values
		setTimeout(() => {
			report.set_filter_value("month", month);
			report.set_filter_value("year", year);
			
			if (url_params.employee) {
				report.set_filter_value("employee", url_params.employee);
			}
			
			report.refresh();
		}, 100);
	},
	"get_datatable_options": function(options) {
		options.showRowIndex = false;
		options.serialNoColumn = false;
		options.layout = "fixed";

		return options;
	}
};
