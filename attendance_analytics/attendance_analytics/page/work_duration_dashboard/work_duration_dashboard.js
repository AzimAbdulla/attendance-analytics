frappe.pages['work_duration_dashboard'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Work Duration Dashboard',
		single_column: true
	});

	// 1. Add Filters
	page.add_field({
		fieldname: 'employee',
		label: __('Employee'),
		fieldtype: 'Link',
		options: 'Employee',
		reqd: 1,
		change: () => refresh_dashboard(page)
	});

	page.add_field({
		fieldname: 'month',
		label: __('Month'),
		fieldtype: 'Select',
		options: "January\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
		default: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"][frappe.datetime.str_to_obj(frappe.datetime.nowdate()).getMonth()],
		change: () => refresh_dashboard(page)
	});

	page.add_field({
		fieldname: 'year',
		label: __('Year'),
		fieldtype: 'Select',
		options: "2024\n2025\n2026\n2027",
		default: frappe.datetime.str_to_obj(frappe.datetime.nowdate()).getFullYear(),
		change: () => refresh_dashboard(page)
	});

	// 2. Dashboard Containers
	const $content = $(wrapper).find(".layout-main-section");
	$content.append(`
		<div id="dashboard-summary" style="display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 30px;"></div>
		<div id="dashboard-chart" style="margin-bottom: 40px; background: var(--card-bg, #fff); padding: 20px; border-radius: 8px; border: 1px solid var(--border-color);"></div>
		<div id="dashboard-table-container">
			<div id="dashboard-table"></div>
		</div>
	`);

	// Initial styling for cards
	frappe.dom.set_style(`
		.dash-card {
			background-color: var(--card-bg, #fff);
			border: 1px solid var(--border-color, #f0f0f0);
			border-bottom: 4px solid #d1d8dd;
			border-radius: 10px;
			padding: 15px 20px;
			min-width: 150px;
			flex: 1;
			box-shadow: 0 4px 10px rgba(0,0,0,0.05);
			display: flex;
			flex-direction: column;
			align-items: flex-start;
		}
		.dash-card-label {
			font-size: 10px;
			text-transform: uppercase;
			font-weight: 700;
			color: var(--text-muted, #8d99ae);
			margin-bottom: 5px;
		}
		.dash-card-value {
			font-size: 1.8rem;
			font-weight: 900;
			line-height: 1;
		}
		.dash-green { border-bottom-color: #2ecc71 !important; color: #27ae60; }
		.dash-red { border-bottom-color: #e74c3c !important; color: #c0392b; }
		.dash-orange { border-bottom-color: #f39c12 !important; color: #d35400; }
		.dash-blue { border-bottom-color: #3498db !important; color: #2980b9; }
		.dash-grey { border-bottom-color: #95a5a6 !important; color: #7f8c8d; }
	`);

	// Auto-load if coming from report (route options)
	if (frappe.route_options && frappe.route_options.employee) {
		page.fields_dict.employee.set_value(frappe.route_options.employee);
		page.fields_dict.month.set_value(frappe.route_options.month);
		page.fields_dict.year.set_value(frappe.route_options.year);
		frappe.route_options = null;
	}

	refresh_dashboard(page);
};

function refresh_dashboard(page) {
	const employee = page.fields_dict.employee.get_value();
	const month = page.fields_dict.month.get_value();
	const year = page.fields_dict.year.get_value();

	if (!employee) return;

	frappe.call({
		method: "attendance_analytics.attendance_analytics.page.work_duration_dashboard.work_duration_dashboard.get_dashboard_data",
		args: { employee, month_name: month, year },
		callback: function(r) {
			if (r.message) {
				render_cards(r.message);
				render_chart(r.message.chart_data);
				render_table(r.message.report_data);
			}
		}
	});
}

function render_cards(data) {
	const $container = $("#dashboard-summary").empty();
	
	const main_stats = [
		{ label: "Present", value: data.counts["Present"], color: "dash-green" },
		{ label: "Absent", value: data.counts["Absent"], color: "dash-red" },
		{ label: "Half Day", value: data.counts["Half Day"], color: "dash-orange" },
		{ label: "WFH", value: data.counts["Work From Home"], color: "dash-blue" },
		{ label: "On Leave", value: data.counts["On Leave"], color: "dash-grey" }
	];

	main_stats.forEach(stat => {
		$container.append(`
			<div class="dash-card ${stat.color}">
				<div class="dash-card-label">${stat.label}</div>
				<div class="dash-card-value">${stat.value}</div>
			</div>
		`);
	});

	// Add dynamic leave types
	Object.keys(data.leave_type_counts).forEach(lt => {
		$container.append(`
			<div class="dash-card dash-grey">
				<div class="dash-card-label">${lt}</div>
				<div class="dash-card-value">${data.leave_type_counts[lt]}</div>
			</div>
		`);
	});
}

function render_chart(chart_data) {
	new frappe.Chart("#dashboard-chart", {
		title: "Daily Work Duration (Hours)",
		data: {
			labels: chart_data.labels,
			datasets: [{ values: chart_data.values }]
		},
		type: 'line',
		height: 250,
		colors: ['#3498db'],
		lineOptions: { regionFill: 1, strokeWidth: 3 },
		axisOptions: { xIsSeries: 1, maxValue: 15 }
	});
}

function render_table(report_data) {
	const columns = [
		{ id: 'date', name: 'Date', width: 120 },
		{ id: 'status', name: 'Status', width: 120 },
		{ id: 'leave_type', name: 'Leave Type', width: 140 },
		{ id: 'first_in', name: 'First In', width: 100 },
		{ id: 'last_out', name: 'Last Out', width: 100 },
		{ id: 'work_hours', name: 'Work Duration', width: 130 }
	];

	const datatable = new frappe.DataTable("#dashboard-table", {
		columns: columns,
		data: report_data,
		layout: 'fixed',
		serialNoColumn: false,
		showRowIndex: false
	});
}
