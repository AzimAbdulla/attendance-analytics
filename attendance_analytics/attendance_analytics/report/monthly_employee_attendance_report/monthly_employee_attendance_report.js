// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Monthly Employee Attendance Report"] = {
	filters: [
		{
			fieldname: "filter_based_on",
			label: __("Filter Based On"),
			fieldtype: "Select",
			options: ["Month", "Date Range"],
			default: "Month",
			reqd: 1,
			on_change: (report) => {
				let filter_based_on = frappe.query_report.get_filter_value("filter_based_on");

				if (filter_based_on == "Month") {
					set_reqd_filter("month", true);
					set_reqd_filter("year", true);
					set_reqd_filter("start_date", false);
					set_reqd_filter("end_date", false);
				}
				if (filter_based_on == "Date Range") {
					set_reqd_filter("month", false);
					set_reqd_filter("year", false);
					set_reqd_filter("start_date", true);
					set_reqd_filter("end_date", true);
				}
				report.refresh();
			},
		},
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			options: [
				{ value: 1, label: __("Jan") },
				{ value: 2, label: __("Feb") },
				{ value: 3, label: __("Mar") },
				{ value: 4, label: __("Apr") },
				{ value: 5, label: __("May") },
				{ value: 6, label: __("June") },
				{ value: 7, label: __("July") },
				{ value: 8, label: __("Aug") },
				{ value: 9, label: __("Sep") },
				{ value: 10, label: __("Oct") },
				{ value: 11, label: __("Nov") },
				{ value: 12, label: __("Dec") },
			],
			default: frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth() + 1,
			depends_on: "eval:doc.filter_based_on == 'Month'",
		},
		{
			fieldname: "start_date",
			label: __("Start Date"),
			fieldtype: "Date",
			depends_on: "eval:doc.filter_based_on == 'Date Range'",
			on_change: validate_date_range,
		},
		{
			fieldname: "end_date",
			label: __("End Date"),
			fieldtype: "Date",
			depends_on: "eval:doc.filter_based_on == 'Date Range'",
			on_change: validate_date_range,
		},
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Select",
			depends_on: "eval:doc.filter_based_on == 'Month'",
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			get_query: () => {
				var company = frappe.query_report.get_filter_value("company");
				return {
					filters: {
						company: company,
					},
				};
			},
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
			get_query: () => {
				var company = frappe.query_report.get_filter_value("company");
				return {
					filters: {
						company: company,
					},
				};
			},
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
		},
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: ["", "Branch", "Grade", "Department", "Designation"],
		},
		{
			fieldname: "include_company_descendants",
			label: __("Include Company Descendants"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "summarized_view",
			label: __("Summarized View"),
			fieldtype: "Check",
			default: 0,
			on_change: (report) => {
				if (report.get_filter_value("summarized_view")) {
					report.set_filter_value("duration_view", 0);
				}
				report.refresh();
			}
		},
		{
			fieldname: "duration_view",
			label: __("Duration View"),
			fieldtype: "Check",
			default: 0,
			on_change: (report) => {
				if (report.get_filter_value("duration_view")) {
					report.set_filter_value("summarized_view", 0);
				}
				report.refresh();
			},
		},
	],
	onload: function () {
		return frappe.call({
			method: "attendance_analytics.attendance_analytics.report.monthly_employee_attendance_report.monthly_employee_attendance_report.get_attendance_years",
			callback: function (r) {
				var year_filter = frappe.query_report.get_filter("year");
				year_filter.df.options = r.message;
				year_filter.df.default = r.message.split("\n")[0];
				year_filter.refresh();
				year_filter.set_input(year_filter.df.default);
			},
		});
	},
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		const summarized_view = frappe.query_report.get_filter_value("summarized_view");
		const group_by = frappe.query_report.get_filter_value("group_by");

		// Column Index Adjustment:
		// If Group By is active, Employee Name is at index 1.
		// If NO Group By is active, Employee Name is at index 0.
		const is_date_column_start = group_by ? 2 : 1;

		if (group_by && column.colIndex === 0) {
			value = "<strong>" + value + "</strong>";
		}

		if (column.fieldname === "employee_name" && data && data.employee) {
			const employee = data.employee_name;

			const onclick_action = `
				const filters = frappe.query_report.get_filter_values();
				const month_map = {
					1: 'January', 2: 'February', 3: 'March', 4: 'April', 
					5: 'May', 6: 'June', 7: 'July', 8: 'August', 
					9: 'September', 10: 'October', 11: 'November', 12: 'December'
				};
				frappe.route_options = {
					'month': month_map[filters.month],
					'year': filters.year,
					'employee': '${employee.replace(/'/g, "\\'")}'
				};
				frappe.set_route('query-report', 'Monthly Work Duration Report');
			`.replace(/\n/g, ' ');

			value = `<a href="javascript:void(0)" onclick="${onclick_action}" class="grey" style="color:var(--text-color); text-decoration: none;" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">${value}</a>`;
		}

		if (!summarized_view) {
			// Check if this is a date column (fieldname is DD-MM-YYYY)
			if (column.fieldname && column.fieldname.includes("-")) {
				const raw_value = data[column.fieldname];
				const duration_view = frappe.query_report.get_filter_value("duration_view");
				
				// Check for tooltip details
				let tooltip = "";
				if (data && data._details && data._details[column.fieldname]) {
					tooltip = data._details[column.fieldname];
				}

				let style = "";
				const status = data._status_map ? data._status_map[column.fieldname] : "";
				const is_audit = ["Present (Unmarked)", "Present (Requested)", "WFH (Requested)", "Leave (Requested)"].includes(status);
				
				if (raw_value == "HD/P") style = "color:#914EE3";
				else if (raw_value == "HD/A" || raw_value == "HD") style = "color:#f1c40f";
				else if (raw_value == "P" || raw_value == "WFH") style = "color:green";
				else if (raw_value == "P(U)") style = "color:#27ae60; font-style: italic;";
				else if (raw_value == "P(RQ)") style = "color:#27ae60; font-style: italic;";
				else if (raw_value == "WFH(RQ)") style = "color:#3187D8; font-style: italic;";
				else if (raw_value == "L(RQ)") style = "color:#318AD8; font-style: italic;";
				else if (raw_value == "A") style = "color:red";
				else if (raw_value && (raw_value == "L" || raw_value.startsWith("L("))) style = "color:#318AD8";
				else if (duration_view && raw_value && raw_value.includes("h ")) {
					if (status && status.includes("Half Day")) {
						style = "color:#f1c40f; font-weight:bold;";
					} else if (is_audit) {
						style = "color:#27ae60; font-weight:bold; font-style: italic;";
					} else {
						style = "color:#43a047; font-weight:bold;";
					}
				}
				else style = "color:#878787";

				// Logic for tooltips and cell wrapping
				const is_duration = duration_view && raw_value && raw_value.includes("h ");
				const is_present = ["P", "P(U)", "P(RQ)", "WFH(RQ)", "L(RQ)"].includes(raw_value);

				if (is_audit) {
					// Absolute positioning for a perfect edge-to-edge fill inside the datatable cell
					const audit_bg = "#fff9c4"; // Softer, less saturated pastel yellow
					const wrapper_style = `position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-color: ${audit_bg}; display: flex; align-items: center; justify-content: center; z-index: 1;`;
					
					if (tooltip && (is_present || is_duration)) {
						value = `<div style="${wrapper_style}"><span title="${tooltip}" style="${style}; cursor:help; display:inline-block; position:relative; z-index:2;">${raw_value}</span></div>`;
					} else {
						value = `<div style="${wrapper_style}"><span style="${style}; display:inline-block; position:relative; z-index:2;">${raw_value || ""}</span></div>`;
					}
				} else {
					// Standard layout for normal items
					if (tooltip && (is_present || is_duration)) {
						value = `<div style="text-align:center; width:100%;"><span title="${tooltip}" style="${style}; cursor:help; display:inline-block;">${raw_value}</span></div>`;
					} else if (style) {
						value = `<div style="text-align:center; width:100%;"><span style="${style}; display:inline-block;">${raw_value || ""}</span></div>`;
					}
				}
			}
		}

		return value;
	},
};
function set_reqd_filter(fieldname, is_reqd) {
	let filter = frappe.query_report.get_filter(fieldname);
	filter.df.reqd = is_reqd;
	filter.refresh();
}
function validate_date_range(report) {
	let start_date = frappe.query_report.get_filter_value("start_date");
	let end_date = frappe.query_report.get_filter_value("end_date");
	if (!(start_date && end_date)) return;

	let start = frappe.datetime.str_to_obj(start_date);
	let end = frappe.datetime.str_to_obj(end_date);
	let milli_seconds_in_a_day = 24 * 60 * 60 * 1000;
	let day_diff = Math.floor((end - start) / milli_seconds_in_a_day);
	if (day_diff > 90) {
		frappe.throw({
			message: __("Please set a date range less than 90 days."),
			title: __("Date Range Exceeded"),
		});
	}
	report.refresh();
}
