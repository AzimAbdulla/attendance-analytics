frappe.query_reports["Monthly Attendance Performance Report"] = {
	"filters": [
		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Select",
			"options": [
				{"value": "01", "label": __("January")},
				{"value": "02", "label": __("February")},
				{"value": "03", "label": __("March")},
				{"value": "04", "label": __("April")},
				{"value": "05", "label": __("May")},
				{"value": "06", "label": __("June")},
				{"value": "07", "label": __("July")},
				{"value": "08", "label": __("August")},
				{"value": "09", "label": __("September")},
				{"value": "10", "label": __("October")},
				{"value": "11", "label": __("November")},
				{"value": "12", "label": __("December")},
			],
			"default": frappe.datetime.now_date().split("-")[1],
			"reqd": 1
		},
		{
			"fieldname": "year",
			"label": __("Year"),
			"fieldtype": "Select",
			"options": [
				{"value": "2023", "label": "2023"},
				{"value": "2024", "label": "2024"},
				{"value": "2025", "label": "2025"},
				{"value": "2026", "label": "2026"},
			],
			"default": frappe.datetime.now_date().split("-")[0],
			"reqd": 1
		},
		{
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options": "Department"
		},
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Branch"
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
		options.layout = "fixed";

		return options;
	},
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname == "employee_name" && data && data.employee) {
			const month_map = {
				"01": "January", "02": "February", "03": "March", "04": "April",
				"05": "May", "06": "June", "07": "July", "08": "August",
				"09": "September", "10": "October", "11": "November", "12": "December"
			};
			const filters = frappe.query_report.get_filter_values();
			const month_name = month_map[filters.month];
			const year = filters.year;
			
			const query_params = frappe.utils.make_query_string({
				month: month_name,
				year: year,
				employee: data.employee_name
			});

			value = `<a href="/app/query-report/Monthly%20Work%20Duration%20Report?${query_params}" class="grey" style="color:var(--text-color); text-decoration: none;" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">${value}</a>`;
		}

		return value;
	}
};
