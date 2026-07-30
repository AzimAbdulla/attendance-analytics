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
			fieldtype: "MultiSelectList",
			options: "Department",
			get_data: function (txt) {
				var company = frappe.query_report.get_filter_value("company");
				return frappe.db.get_link_options("Department", txt, {
					company: company,
				});
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
		{
			fieldname: "request",
			label: __("With Request"),
			fieldtype: "Check",
			default: 0,
			on_change: (report) => {
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
	after_datatable_render: function (datatable) {
		// Freeze the row-number column, the optional Group By column, and Employee Name
		// so they stay put while scrolling horizontally through the day/summary columns.
		const columns = datatable.datamanager.getColumns();
		const freeze_upto = columns.findIndex((col) => col.id === "employee_name");
		if (freeze_upto === -1) return;

		let left = 0;
		for (let i = 0; i <= freeze_upto; i++) {
			const width = columns[i].width || 0;
			// z-index is deliberately way above what the formatter uses internally (its
			// value spans, worklog dots, and audit/duration background overlays go up to
			// z-index:3) — those inner spans sit on non-frozen cells that don't establish
			// their own stacking context, so their z-index bubbles up and ties directly
			// against a frozen cell's z-index at a shared ancestor level. On a tie, DOM
			// order wins, and later (non-frozen) columns would paint over the frozen ones.
			datatable.style.setStyle(`.dt-cell--col-${i}`, {
				position: "sticky",
				left: `${left}px`,
				"z-index": "10",
				background: "var(--dt-cell-bg)",
				"will-change": "transform",
			});
			datatable.style.setStyle(`.dt-cell--header.dt-cell--col-${i}`, {
				"z-index": "11",
				background: "var(--dt-header-cell-bg)",
			});
			// The filter/search row's cells only carry `.dt-cell--filter`, not
			// `.dt-cell--header` — without this they'd share the body's z-index and,
			// being earlier in paint order than the (later-in-DOM) scrolled body rows,
			// would get visually painted OVER by row text during vertical scroll.
			datatable.style.setStyle(`.dt-cell--filter.dt-cell--col-${i}`, {
				"z-index": "11",
				background: "var(--dt-cell-bg)",
			});
			if (i === freeze_upto) {
				datatable.style.setStyle(`.dt-cell--col-${i}`, {
					"box-shadow": "2px 0 4px -2px rgba(0, 0, 0, 0.25)",
				});
			}
			left += width;
		}

		// The header row AND the column filter/search row both live inside the same
		// `.dt-header` container, which is kept horizontally in sync with the body via
		// `transform: translateX(-scrollLeft)` on that whole container. That ancestor
		// transform re-anchors `position: sticky` on its children to itself instead of
		// the real scroll viewport, so both the frozen header label and the filter input
		// for that column would drift out of view even though the body cells beneath
		// them correctly stay put. Counteract it with an equal-and-opposite transform on
		// every matching cell (header label cell + filter row cell) for each column.
		if (datatable.bodyScrollable && datatable.header) {
			if (datatable._frozenHeaderScrollHandler) {
				datatable.bodyScrollable.removeEventListener("scroll", datatable._frozenHeaderScrollHandler);
			}
			const apply_header_freeze = () => {
				const scroll_left = datatable.bodyScrollable.scrollLeft;
				for (let i = 0; i <= freeze_upto; i++) {
					datatable.header.querySelectorAll(`.dt-cell--col-${i}`).forEach((cell) => {
						cell.style.transform = `translateX(${scroll_left}px)`;
					});
				}
			};
			datatable._frozenHeaderScrollHandler = () => requestAnimationFrame(apply_header_freeze);
			datatable.bodyScrollable.addEventListener("scroll", datatable._frozenHeaderScrollHandler);
			apply_header_freeze();
		}
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
				const request_view = frappe.query_report.get_filter_value("request");

				// When "Request" is checked, pending/unmarked days are shown as if
				// already approved: text and styling fall back to the confirmed status.
				let effective_status = status;
				let display_value = raw_value;
				if (request_view) {
					if (status === "Present (Unmarked)" || status === "Present (Requested)") {
						effective_status = "Present";
						display_value = "P";
					} else if (status === "WFH (Requested)") {
						effective_status = "Work From Home";
						display_value = "WFH";
					} else if (status === "Leave (Requested)") {
						effective_status = "On Leave";
						const pending_abbr = data._pending_leave_type && data._pending_leave_type[column.fieldname];
						display_value = pending_abbr ? `L(${pending_abbr})` : "L";
					}
				}

				const is_audit = ["Present (Unmarked)", "Present (Requested)", "WFH (Requested)", "Leave (Requested)"].includes(effective_status);

				if (raw_value == "HD/P") style = "color:#914EE3";
				else if (raw_value == "HD/A" || raw_value == "HD") style = "color:#f1c40f";
				else if (display_value == "P" || display_value == "WFH") style = "color:green";
				else if (display_value == "P(U)") style = "color:#27ae60; font-style: italic;";
				else if (display_value == "P(RQ)") style = "color:#27ae60; font-style: italic;";
				else if (display_value == "WFH(RQ)") style = "color:#3187D8; font-style: italic;";
				else if (display_value && display_value.startsWith("L(RQ")) style = "color:#318AD8; font-style: italic;";
				else if (display_value == "A") style = "color:red";
				else if (display_value && (display_value == "L" || display_value.startsWith("L("))) {
					if (display_value.includes("PL")) style = "color:#1976d2; font-weight:bold;"; // Deep Blue
					else if (display_value.includes("SL")) style = "color:#f4511e; font-weight:bold;"; // Orange
					else if (display_value.includes("CL")) style = "color:#00acc1; font-weight:bold;"; // Teal
					else if (display_value.includes("CO")) style = "color:#8e24aa; font-weight:bold;"; // Purple
					else if (display_value.includes("LWP")) style = "color:#8d6e63; font-weight:bold;"; // Grey/Brown
					else style = "color:#318AD8; font-weight:bold;"; // Default Blue
				}
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

				let inner_html = "";
				if (is_duration) {
					// Convert DD-MM-YYYY to YYYY-MM-DD
					const date_parts = column.fieldname.split("-");
					const formatted_date = `${date_parts[2]}-${date_parts[1]}-${date_parts[0]}`;
					const emp = (data.employee || "").replace(/'/g, "\\'");
					const onclick_action = `frappe.route_options={'employee':'${emp}','time':['between',['${formatted_date} 00:00:00','${formatted_date} 23:59:59']]};frappe.set_route('List','Employee Checkin');`.replace(/\n/g, ' ');
					
					inner_html = `<a href="javascript:void(0)" onclick="${onclick_action}" title="${tooltip || ''}" style="${style}; cursor:pointer; text-decoration:none; display:inline-block; position:relative; z-index:2;" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">${raw_value}</a>`;
				} else if (tooltip && is_present) {
					inner_html = `<span title="${tooltip}" style="${style}; cursor:help; display:inline-block; position:relative; z-index:2;">${display_value}</span>`;
				} else {
					inner_html = `<span style="${style}; display:inline-block; position:relative; z-index:2;">${display_value || ""}</span>`;
				}

				// --- WORKLOG DOT INDICATOR ---
				const active_presence = ["Present", "Work From Home", "Half Day/Other Half Present", "Half Day/Other Half Absent", "Half Day", "Present (Unmarked)", "Present (Requested)", "WFH (Requested)"];
				const has_worklog = data && data._worklogs && data._worklogs[column.fieldname];
				const is_active_day = active_presence.includes(status);

				if (has_worklog || is_active_day) {
					const dot_color = has_worklog ? "#2196F3" : "#F44336"; // Vibrant Material Colors
					const dot_title = has_worklog ? (tooltip || "") : __("No worklogs found for this day");
					const dot_html = `<span style="width: 8px; height: 8px; background-color: ${dot_color}; border-radius: 50%; position: absolute; top: -4px; right: -10px; z-index: 3; border: 1px solid white;" title="${dot_title}"></span>`;
					inner_html = `<div style="position: relative; display: inline-block;">${inner_html}${dot_html}</div>`;
				}

				if (is_audit) {
					// Absolute positioning for a perfect edge-to-edge fill inside the datatable cell
					const audit_bg = "#e3f2fd"; // Soft, light blue
					const wrapper_style = `position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-color: ${audit_bg}; display: flex; align-items: center; justify-content: center; z-index: 1;`;
					value = `<div style="${wrapper_style}">${inner_html}</div>`;
				} else if (is_duration && (effective_status === "Present" || effective_status === "Work From Home")) {
					// Dynamic highlight for Present duration (exclude HD and Audits)
					let dur_bg = "";
					const hours = parseInt(raw_value.split("h")[0]) || 0;
					
					if (hours >= 7) dur_bg = "#e8f5e9"; // Light Green
					else if (hours >= 6) dur_bg = "#fff9c4"; // Light Yellow
					else dur_bg = "#ffebee"; // Light Red

					const wrapper_style = `position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-color: ${dur_bg}; display: flex; align-items: center; justify-content: center; z-index: 1;`;
					value = `<div style="${wrapper_style}">${inner_html}</div>`;
				} else {
					// Standard layout for normal items
					value = `<div style="text-align:center; width:100%;">${inner_html}</div>`;
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
