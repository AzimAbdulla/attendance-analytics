// Copyright (c) 2026, Azim Abdulla and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly Work Duration Report"] = {
	"filters": [
		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Select",
			"options": "January\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
			"default": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"][frappe.datetime.str_to_obj(frappe.datetime.nowdate()).getMonth()],
			"reqd": 1
		},
		{
			"fieldname": "year",
			"label": __("Year"),
			"fieldtype": "Select",
			"options": "2024\n2025\n2026\n2027",
			"default": frappe.datetime.str_to_obj(frappe.datetime.nowdate()).getFullYear(),
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
		if (url_params.month || url_params.year || url_params.employee) {
			// Small timeout ensures the default filter setup finishes before we override it
			setTimeout(() => {
				if (url_params.month) report.set_filter_value("month", url_params.month);
				if (url_params.year) report.set_filter_value("year", url_params.year);
				if (url_params.employee) report.set_filter_value("employee", url_params.employee);
				report.refresh();
			}, 500);
		}
	},
	"get_datatable_options": function(options) {
		options.showRowIndex = false;
		options.serialNoColumn = false;
		options.layout = "fixed";

		return options;
	}
};
