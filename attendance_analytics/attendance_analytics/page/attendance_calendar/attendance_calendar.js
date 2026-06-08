frappe.pages['attendance_calendar'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Employee Attendance Calendar'),
		single_column: true
	});

	// 1. Setup Filters
	let employee_field = page.add_field({
		fieldname: 'employee',
		label: __('Employee'),
		fieldtype: 'Link',
		options: 'Employee',
		reqd: 1,
		change: () => refresh_calendar(page, wrapper)
	});

	// Permission logic
	const roles = frappe.user.roles || [];
	const is_admin = roles.includes("System Manager") || roles.includes("HR Manager") || roles.includes("HR User");

	if (!is_admin) {
		frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name", (r) => {
			if (r && r.name) {
				employee_field.set_value(r.name);
				employee_field.df.read_only = 1;
				employee_field.refresh();
			}
		});
	}

	page.add_field({
		fieldname: 'month',
		label: __('Month'),
		fieldtype: 'Select',
		options: ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"].map(m => {
			return { value: m, label: moment().month(m-1).format("MMMM") };
		}),
		default: moment().month() + 1,
		change: () => refresh_calendar(page, wrapper)
	});

	page.add_field({
		fieldname: 'year',
		label: __('Year'),
		fieldtype: 'Select',
		options: ["2024", "2025", "2026", "2027"],
		default: moment().format("YYYY"),
		change: () => refresh_calendar(page, wrapper)
	});

	// 2. Setup Layout
	const $content = $(wrapper).find(".layout-main-section");
	$content.empty().append(`
		<div id="calendar-container" style="padding: 20px 0; overflow-x: auto;">
			<div id="calendar-grid" class="att-calendar-grid"></div>
		</div>
		<div id="detail-sidebar" class="att-sidebar">
			<div class="sidebar-header">
				<h3 style="margin:0;">${__('Calculation Breakdown')}</h3>
				<button class="btn btn-xs btn-default close-sidebar">&times;</button>
			</div>
			<div class="sidebar-body">
				<div class="text-muted text-center" style="padding-top: 50px;">
					${__('Select a day to view details')}
				</div>
			</div>
		</div>
	`);

	// 3. Styles
	frappe.dom.set_style(`
		.att-calendar-grid {
			display: grid;
			grid-template-columns: repeat(7, minmax(100px, 1fr));
			gap: 12px;
			user-select: none;
			min-width: 700px;
		}
		.calendar-day-header {
			text-align: center;
			font-weight: bold;
			font-size: 12px;
			text-transform: uppercase;
			color: var(--text-muted);
			padding-bottom: 10px;
		}
		.calendar-day-box {
			background: var(--card-bg, #fff);
			border: 1px solid var(--border-color);
			border-radius: 8px;
			min-height: 110px;
			padding: 10px;
			position: relative;
			cursor: pointer;
			transition: all 0.2s ease;
			display: flex;
			flex-direction: column;
			justify-content: space-between;
		}
		.calendar-day-box:hover {
			box-shadow: 0 4px 12px rgba(0,0,0,0.1);
			transform: translateY(-2px);
			border-color: var(--primary-color);
		}
		.day-num { font-weight: 800; font-size: 1.1rem; color: var(--text-color); }
		.day-status { font-size: 10px; text-transform: uppercase; font-weight: 700; margin-top: auto; padding-bottom: 5px; }
		.day-duration { font-size: 12px; font-weight: 600; color: #27ae60; }
		
		/* Heatmap Backgrounds */
		.bg-green { background-color: #e8f5e9 !important; border-color: #c8e6c9 !important; }
		.bg-yellow { background-color: #fff9c4 !important; border-color: #fff59d !important; }
		.bg-red { background-color: #ffebee !important; border-color: #ffcdd2 !important; }
		.bg-grey { background-color: #f5f5f5 !important; opacity: 0.6; }
		.bg-audit { background-color: #e3f2fd !important; border-color: #bbdefb !important; }

		/* Sidebar */
		.att-sidebar {
			position: fixed;
			top: 0; right: -400px;
			width: 380px; height: 100%;
			background: #fff;
			box-shadow: -4px 0 15px rgba(0,0,0,0.1);
			z-index: 1050;
			transition: right 0.3s ease;
			display: flex;
			flex-direction: column;
		}
		.att-sidebar.active { right: 0; }
		.sidebar-header { padding: 15px 20px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; }
		.sidebar-body { padding: 20px; overflow-y: auto; flex: 1; }
		.log-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed #eee; font-size: 13px; }
		.cluster-box { background: #f8f9fa; padding: 12px; border-radius: 6px; margin-bottom: 15px; border-left: 4px solid var(--primary-color); }
		.math-row { display: flex; justify-content: space-between; margin-top: 5px; font-weight: bold; }
	`);

	// 4. Events
	$(wrapper).on('click', '.close-sidebar', () => {
		$content.find('#detail-sidebar').removeClass('active');
	});

	refresh_calendar(page, wrapper);
};

function refresh_calendar(page, wrapper) {
	const filters = page.get_values();
	if (!filters.employee) return;

	frappe.call({
		method: 'attendance_analytics.attendance_analytics.page.attendance_calendar.attendance_calendar.get_calendar_data',
		args: {
			employee: filters.employee,
			month: filters.month,
			year: filters.year
		},
		callback: function(r) {
			if (r.message) {
				render_calendar(r.message, filters.month, filters.year, wrapper);
			}
		}
	});
}

function render_calendar(data, month, year, wrapper) {
	const $grid = $("#calendar-grid").empty();
	const days_in_month = moment(`${year}-${month}`, "YYYY-M").daysInMonth();
	const first_day_weekday = moment(`${year}-${month}-01`, "YYYY-M-D").weekday(); // 0 (Sun) to 6 (Sat)

	// Add Headers
	["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].forEach(d => {
		$grid.append(`<div class="calendar-day-header">${d}</div>`);
	});

	// Add Empty Offsets
	for (let i = 0; i < first_day_weekday; i++) {
		$grid.append(`<div class="calendar-day-empty"></div>`);
	}

	// Add Days
	for (let i = 1; i <= days_in_month; i++) {
		const date_str = `${year}-${String(month).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
		const day_data = data.days[date_str] || {};
		
		let bg_class = "";
		if (day_data.status === "Holiday" || day_data.status === "Weekly Off") bg_class = "bg-grey";
		else if (day_data.is_audit) bg_class = "bg-audit";
		else if (day_data.work_hours >= 7) bg_class = "bg-green";
		else if (day_data.work_hours >= 6) bg_class = "bg-yellow";
		else if (day_data.work_hours > 0) bg_class = "bg-red";

		const $day = $(`
			<div class="calendar-day-box ${bg_class}" data-date="${date_str}">
				<div class="day-num">${i}</div>
				<div class="day-status" style="color: ${get_status_color(day_data.status)}">${day_data.status || ""}</div>
				<div class="day-duration">${day_data.work_duration !== "0h 00m" ? day_data.work_duration : ""}</div>
			</div>
		`).appendTo($grid);

		$day.on('click', () => show_details(date_str, day_data));
	}
}

function get_status_color(status) {
	if (!status) return "transparent";
	if (status.includes("Present") || status === "Work From Home") return "#2e7d32";
	if (status === "Absent") return "#d32f2f";
	if (status.includes("Leave")) return "#7b1fa2";
	return "#757575";
}

function show_details(date, data) {
	const $sidebar = $('#detail-sidebar');
	const $body = $sidebar.find('.sidebar-body').empty();

	$sidebar.addClass('active');

	let html = `
		<div style="margin-bottom: 25px;">
			<h4 style="margin:0;">${moment(date).format("dddd, Do MMMM")}</h4>
			<div style="margin-top: 8px; display: inline-block; padding: 4px 10px; background: #e0e0e0; border-radius: 4px; font-weight: bold; font-size: 11px; text-transform: uppercase;">
				${data.status}
			</div>
		</div>

		<div class="section-title" style="font-weight:bold; margin-bottom:10px; border-bottom: 1px solid #eee; padding-bottom:5px;">
			📊 Calculation Logic: Clustered Greedy
		</div>
	`;

	if (data.clusters && data.clusters.length > 0) {
		data.clusters.forEach((c, idx) => {
			html += `
				<div class="cluster-box">
					<div style="font-size:11px; text-transform:uppercase; color:var(--text-muted);">Session ${idx + 1}</div>
					<div style="display:flex; justify-content:space-between; margin-top:5px;">
						<span><b>IN:</b> ${c.in}</span>
						<span><b>OUT:</b> ${c.out}</span>
					</div>
					<div style="margin-top:8px; font-size:12px; color:#2e7d32;">
						<b>Duration:</b> ${c.duration} ${c.note ? `<i>(${c.note})</i>` : ''}
					</div>
				</div>
			`;
		});

		html += `
			<div style="background:#fffde7; padding:15px; border-radius:8px; border:1px solid #ffe082; margin-top:10px;">
				<div class="math-row"><span>Total Work:</span> <span style="color:#2e7d32;">${data.work_duration}</span></div>
				<div class="math-row"><span>Total Break:</span> <span style="color:#f4511e;">${data.break_duration}</span></div>
			</div>
		`;
	}

	html += `
		<div class="section-title" style="font-weight:bold; margin-top:30px; margin-bottom:10px; border-bottom: 1px solid #eee; padding-bottom:5px;">
			🕒 Raw Log Timeline
		</div>
	`;

	if (data.logs && data.logs.length > 0) {
		data.logs.forEach(l => {
			const type_color = l.type === "IN" ? "green" : "red";
			html += `
				<div class="log-row">
					<span><b style="color:${type_color}">${l.type}</b> at ${l.time}</span>
					<span class="text-muted" style="font-size:11px;">Dev: ${l.device}</span>
				</div>
			`;
		});
	} else {
		html += `<div class="text-muted text-center" style="padding:20px;">No biometric logs found for this day.</div>`;
	}

	$body.append(html);
}