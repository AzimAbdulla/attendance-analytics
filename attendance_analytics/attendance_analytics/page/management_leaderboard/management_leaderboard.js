frappe.pages['management-leaderboard'].on_page_load = function(wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Management Leaderboard',
		single_column: true
	});

	const now = frappe.datetime.now_date();
	const current_month = now.split("-")[1];
	const current_year = now.split("-")[0];

	// Use add_select for standard Frappe look
	page.month_select = page.add_select(__('Month'), [
		{value: '01', label: __('January')},
		{value: '02', label: __('February')},
		{value: '03', label: __('March')},
		{value: '04', label: __('April')},
		{value: '05', label: __('May')},
		{value: '06', label: __('June')},
		{value: '07', label: __('July')},
		{value: '08', label: __('August')},
		{value: '09', label: __('September')},
		{value: '10', label: __('October')},
		{value: '11', label: __('November')},
		{value: '12', label: __('December')},
	]);
	page.month_select.val(current_month);

	page.year_select = page.add_select(__('Year'), [
		{value: '2024', label: '2024'},
		{value: '2025', label: '2025'},
		{value: '2026', label: '2026'},
	]);
	page.year_select.val(current_year);

	// Event listeners for selects
	page.month_select.on('change', () => render_dashboard(wrapper, page));
	page.year_select.on('change', () => render_dashboard(wrapper, page));

	page.set_primary_action('Refresh', () => {
		render_dashboard(wrapper, page);
	}, 'refresh');

	page.show_form();
	render_dashboard(wrapper, page);
}

function render_dashboard(wrapper, page) {
	const filters = {
		month: page.month_select.val(),
		year: page.year_select.val()
	};

	frappe.call({
		method: 'attendance_analytics.attendance_analytics.page.management_leaderboard.management_leaderboard.get_dashboard_data',
		args: {
			filters: filters
		},
		callback: function(r) {
			if (r.message) {
				const data = r.message;
				$(wrapper).find('.layout-main-section').html(get_dashboard_template(data));
				setup_search(wrapper, data.leaderboard);
			}
		}
	});
}

function get_dashboard_template(data) {
	const leaderboard = data.leaderboard;

	return `
		<style>
			.dashboard-container { padding: 20px; background: #f8f9fa; }
			.kpi-row { display: flex; gap: 20px; margin-bottom: 30px; }
			.kpi-card { 
				flex: 1; background: #fff; padding: 20px; border-radius: 12px; 
				box-shadow: 0 4px 12px rgba(0,0,0,0.05); text-align: center;
			}
			.kpi-value { font-size: 24px; font-weight: bold; color: var(--primary-color); }
			.kpi-label { font-size: 14px; color: #6c757d; margin-top: 5px; }

			.leaderboard-section { background: #fff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); overflow: hidden; }
			.search-bar-container { padding: 15px 20px; border-bottom: 1px solid #f1f1f1; }
			.list-container { max-height: 600px; overflow-y: auto; }
			.leaderboard-row { 
				display: flex; align-items: center; padding: 12px 20px; border-bottom: 1px solid #f8f9fa;
				transition: background 0.2s;
			}
			.leaderboard-row:hover { background: #fcfcfc; }
			.col-rank { width: 60px; font-weight: bold; color: #adb5bd; }
			.col-name { flex: 1; font-weight: 500; }
			.col-score { width: 80px; text-align: right; font-weight: bold; color: var(--primary-color); }
		</style>

		<div class="dashboard-container">
			<div class="kpi-row">
				<div class="kpi-card"><div class="kpi-value">${data.kpis.highest_score}</div><div class="kpi-label">Highest Score</div></div>
				<div class="kpi-card"><div class="kpi-value">${data.kpis.avg_score}</div><div class="kpi-label">Average Score</div></div>
				<div class="kpi-card"><div class="kpi-value">${data.kpis.total_ranked}</div><div class="kpi-label">Ranked Employees</div></div>
			</div>

			<div class="leaderboard-section">
				<div class="search-bar-container">
					<input type="text" class="form-control leaderboard-search" placeholder="Search employee name...">
				</div>
				<div class="list-container">
					${leaderboard.map(emp => `
						<div class="leaderboard-row" data-name="${emp.employee_name.toLowerCase()}">
							<div class="col-rank">#${emp.rank}</div>
							<div class="col-name">${emp.employee_name}</div>
							<div class="col-score">${emp.final_score}</div>
						</div>
					`).join('')}
				</div>
			</div>
		</div>
	`;
}

function setup_search(wrapper, leaderboard) {
	$(wrapper).find('.leaderboard-search').on('keyup', function() {
		const val = $(this).val().toLowerCase();
		$(wrapper).find('.leaderboard-row').each(function() {
			const name = $(this).data('name');
			$(this).toggle(name.includes(val));
		});
	});
}
