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
	"get_chart_options": function(options) {
		options.tooltipOptions = {
			formatTooltipX: (label) => {
				if (!frappe.query_report.data) return label;

				const row = frappe.query_report.data.find(d => {
					let d_date = d.date;
					if (d_date.includes("<span")) d_date = $(d_date).text();
					return d_date.endsWith("-" + label);
				});

				if (row) {
					let pure_date = row.date;
					if (pure_date.includes("<span")) pure_date = $(pure_date).text();
					
					let header = `Date: ${pure_date}`;
					let details = "";

					const status = row.status || "";
					if (status === "On Leave" || status.includes("Leave")) {
						details = `Status: Leave<br>Leave Type: ${row.leave_type || "N/A"}`;
					} else if (status === "Absent") {
						details = `Status: Absent`;
					} else if (status === "Holiday" || status === "Weekly Off") {
						details = `Status: ${status}`;
					} else if (status.includes("Present") || status.includes("WFH") || status.includes("Home") || status.includes("Half Day")) {
						details = `Work Duration: ${row.work_duration}<br>Break Duration: ${row.break_duration}`;
					}
					
					return details ? `${header}<br>${details}` : header;
				}
				return label;
			},
			formatTooltipY: (value) => value + "h"
		};
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
	},
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "work_duration" && value && value !== "0h 00m") {
			value = `<span style="color: #28a745; font-weight: bold;">${value}</span>`;
		}

		return value;
	}
};
