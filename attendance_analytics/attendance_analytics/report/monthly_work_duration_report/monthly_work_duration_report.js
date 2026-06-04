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
		// Modern Elevated Card Styling
		frappe.dom.set_style(`
			.duration-report-cards .report-summary {
				display: flex !important;
				flex-wrap: wrap !important;
				gap: 16px !important;
				padding: 20px 0 40px 0 !important;
				background-color: transparent !important;
				border: none !important;
			}
			.duration-report-cards .summary-item {
				background-color: var(--card-bg, #fff) !important;
				border: 1px solid var(--border-color, #f0f0f0) !important;
				border-bottom: 4px solid #d1d8dd !important; /* Bottom accent */
				border-radius: 10px !important;
				padding: 20px !important;
				min-width: 170px !important;
				flex: 0 1 auto !important;
				box-shadow: 0 4px 10px rgba(0,0,0,0.05) !important;
				display: flex !important;
				flex-direction: column !important;
				align-items: flex-start !important;
				justify-content: center !important;
				margin: 0 !important;
				transition: all 0.3s ease !important;
			}
			.duration-report-cards .summary-item:hover {
				box-shadow: 0 8px 20px rgba(0,0,0,0.1) !important;
				transform: translateY(-3px) !important;
			}
			.duration-report-cards .summary-label {
				order: 1 !important;
				font-size: 11px !important;
				text-transform: uppercase !important;
				font-weight: 700 !important;
				letter-spacing: 0.05em !important;
				color: var(--text-muted, #8d99ae) !important;
				margin-bottom: 10px !important;
				line-height: 1 !important;
			}
			.duration-report-cards .summary-value {
				order: 2 !important;
				font-size: 2.2rem !important;
				font-weight: 900 !important;
				line-height: 1 !important;
				display: block !important;
			}
			/* Vibrant Theme Colors for Cards */
			.duration-report-cards .summary-item.indicator-green { border-bottom-color: #2ecc71 !important; }
			.duration-report-cards .summary-item.indicator-green .summary-value { color: #27ae60 !important; }
			
			.duration-report-cards .summary-item.indicator-red { border-bottom-color: #e74c3c !important; }
			.duration-report-cards .summary-item.indicator-red .summary-value { color: #c0392b !important; }
			
			.duration-report-cards .summary-item.indicator-orange { border-bottom-color: #f39c12 !important; }
			.duration-report-cards .summary-item.indicator-orange .summary-value { color: #d35400 !important; }
			
			.duration-report-cards .summary-item.indicator-blue { border-bottom-color: #3498db !important; }
			.duration-report-cards .summary-item.indicator-blue .summary-value { color: #2980b9 !important; }
			
			.duration-report-cards .summary-item.indicator-grey { border-bottom-color: #95a5a6 !important; }
			.duration-report-cards .summary-item.indicator-grey .summary-value { color: #7f8c8d !important; }
		`);
	},
	"after_datatable_render": function(report) {
		// Ensure the report container has the custom class for styling
		if (report.container) {
			$(report.container).addClass("duration-report-cards");
		}
	}
};
