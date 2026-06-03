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
	"get_datatable_options": function(options) {
		options.showRowIndex = false;
		options.serialNoColumn = false;
		options.layout = "fixed";

		return options;
	},
	"onload": function(report) {
		// Use a slight delay to ensure the container is fully initialized in the DOM
		setTimeout(() => {
			if (frappe.query_report && frappe.query_report.container) {
				frappe.query_report.container.addClass("duration-report-container");
			}
		}, 100);

		frappe.dom.set_style(`
			.duration-report-container .report-summary {
				display: flex !important;
				flex-wrap: wrap !important;
				gap: 12px !important;
				padding: 10px 0 30px 0 !important;
				height: auto !important;
				overflow: visible !important;
			}
			.duration-report-container .summary-item {
				background-color: var(--card-bg, #fff) !important;
				border: 1px solid var(--border-color, #d1d8dd) !important;
				border-radius: var(--border-radius-md, 8px) !important;
				padding: 12px 15px !important;
				min-width: 145px;
				height: auto !important;
				box-shadow: var(--card-shadow, 0 1px 3px rgba(0,0,0,0.1)) !important;
				flex: 1;
				display: flex;
				flex-direction: column; 
				align-items: flex-start;
				margin: 0 !important;
			}
			.duration-report-container .summary-label {
				font-size: 10px !important;
				text-transform: uppercase;
				font-weight: 600;
				color: var(--text-muted, #687178);
				margin-bottom: 6px !important;
			}
			.duration-report-container .summary-value {
				font-size: 1.5rem !important;
				font-weight: 700 !important;
				line-height: 1 !important;
				display: block !important;
			}
			/* Theme-safe High Specificity Colors for Numbers */
			.duration-report-container div.summary-item.indicator-green span.summary-value { color: #28a745 !important; }
			.duration-report-container div.summary-item.indicator-red span.summary-value { color: #dc3545 !important; }
			.duration-report-container div.summary-item.indicator-orange span.summary-value { color: #fd7e14 !important; }
			.duration-report-container div.summary-item.indicator-blue span.summary-value { color: #3498db !important; }
			.duration-report-container div.summary-item.indicator-grey span.summary-value { color: #6c757d !important; }
		`);
	}
};
