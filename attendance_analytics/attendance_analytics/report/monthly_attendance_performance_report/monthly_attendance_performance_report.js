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
		options.layout = "fluid";
		
		if (options.columns) {
			options.columns[0].fixed = true; // Rank
			options.columns[1].fixed = true; // Employee Name (linked)
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
