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
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nPresent\nAbsent\nHalf Day\nWork From Home\nOn Leave"
		},
		{
			"fieldname": "leave_type",
			"label": __("Leave Type"),
			"fieldtype": "Link",
			"options": "Leave Type"
		}
	],
	"get_datatable_options": function(options) {
		options.showRowIndex = false;
		options.serialNoColumn = false;
		options.layout = "fixed";

		return options;
	},
	"onload": function(report) {
		// Static Dashboard Card Design (No Interactivity)
		frappe.dom.set_style(`
			div[data-report-name="Monthly Work Duration Report"] .report-summary {
				display: flex !important;
				flex-wrap: wrap !important;
				gap: 16px !important;
				padding: 24px 0 !important;
				background-color: transparent !important;
				border: none !important;
			}
			div[data-report-name="Monthly Work Duration Report"] .summary-item {
				background-color: var(--card-bg, #ffffff) !important;
				border: 1px solid var(--border-color, #d1d8dd) !important;
				border-radius: 8px !important;
				padding: 16px 20px !important;
				min-width: 160px !important;
				flex: 1 !important;
				box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
				display: flex !important;
				flex-direction: column !important;
				align-items: flex-start !important;
				justify-content: center !important;
				margin: 0 !important;
			}
			div[data-report-name="Monthly Work Duration Report"] .summary-label {
				font-size: 11px !important;
				text-transform: uppercase !important;
				font-weight: 700 !important;
				letter-spacing: 0.04em !important;
				color: var(--text-muted, #687178) !important;
				margin-bottom: 8px !important;
			}
			div[data-report-name="Monthly Work Duration Report"] .summary-value {
				font-size: 1.8rem !important;
				font-weight: 800 !important;
				line-height: 1.2 !important;
				display: block !important;
			}
			/* Colored Indicator Values */
			div[data-report-name="Monthly Work Duration Report"] .summary-item.indicator-green .summary-value { color: #28a745 !important; }
			div[data-report-name="Monthly Work Duration Report"] .summary-item.indicator-red .summary-value { color: #dc3545 !important; }
			div[data-report-name="Monthly Work Duration Report"] .summary-item.indicator-orange .summary-value { color: #fd7e14 !important; }
			div[data-report-name="Monthly Work Duration Report"] .summary-item.indicator-blue .summary-value { color: #007bff !important; }
			div[data-report-name="Monthly Work Duration Report"] .summary-item.indicator-grey .summary-value { color: #6c757d !important; }
		`);
	}
};
