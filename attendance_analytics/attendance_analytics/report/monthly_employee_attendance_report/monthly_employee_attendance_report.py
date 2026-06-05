# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from calendar import monthrange
from datetime import date
from itertools import groupby

from pypika import Field
from pypika.terms import Criterion

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Count, Extract, Sum
from frappe.utils import cint, cstr, formatdate, getdate, get_datetime, add_days, add_months
from frappe.utils.nestedset import get_descendants_of

from hrms.utils import date_diff, get_date_range

Filters = frappe._dict

status_map = {
	"Present": "P",
	"Absent": "A",
	"Half Day/Other Half Absent": "HD/A",
	"Half Day/Other Half Present": "HD/P",
	"Work From Home": "WFH",
	"On Leave": "L",
	"Holiday": "H",
	"Weekly Off": "WO",
	"Present (Unmarked)": "P(U)",
	"Present (Requested)": "P(RQ)",
	"WFH (Requested)": "WFH(RQ)",
	"Leave (Requested)": "L(RQ)",
}

# Priority: Higher number = higher priority
STATUS_PRIORITY = {
	"Present": 10,
	"Work From Home": 10,
	"Half Day/Other Half Present": 9,
	"Half Day/Other Half Absent": 8,
	"On Leave": 7,
	"Absent": 6,
	"Leave (Requested)": 5.8,
	"WFH (Requested)": 5.5,
	"Present (Requested)": 5.2,
	"Present (Unmarked)": 5,
	"Holiday": 2,
	"Weekly Off": 1
}

day_abbr = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def execute(filters: Filters | None = None) -> tuple:
	filters = frappe._dict(filters or {})

	if not filters.filter_based_on:
		frappe.throw(_("Please select Filter Based On"))

	if filters.filter_based_on == "Month" and not (filters.month and filters.year):
		frappe.throw(_("Please select month and year."))

	if filters.filter_based_on == "Date Range":
		if not (filters.start_date and filters.end_date):
			frappe.throw(_("Please set the date range."))
		if getdate(filters.start_date) > getdate(filters.end_date):
			frappe.throw(_("Start date cannot be greater than end date."))
		if date_diff(filters.end_date, filters.start_date) > 90:
			frappe.throw(_("Please set a date range less than 90 days."))

	if not filters.company:
		frappe.throw(_("Please select company."))

	if filters.company:
		filters.companies = [filters.company]
		if filters.include_company_descendants:
			filters.companies.extend(get_descendants_of("Company", filters.company))

	attendance_map = get_attendance_map(filters)
	
	# Fetch auxiliary data for audit and tooltips
	checkin_map = get_checkin_map(filters)
	leave_details_map = get_leave_details_map(filters)
	request_map = get_request_map(filters)
	leave_app_map = get_leave_application_map(filters)

	columns = get_columns(filters)
	data = get_data(filters, attendance_map, checkin_map, leave_details_map, request_map, leave_app_map)

	if not data:
		frappe.msgprint(_("No attendance records found for this criteria."), alert=True, indicator="orange")
		return columns, [], None, None

	message = get_message() if not filters.summarized_view else ""
	chart = get_chart_data(attendance_map, filters)

	return columns, data, message, chart


def get_checkin_map(filters):
	"""Returns a map of checkins: { employee: { date: [logs] } }"""
	start_date, end_date = get_report_date_range(filters)
	
	conditions = {
		"time": ["between", [get_datetime(f"{start_date} 00:00:00"), get_datetime(f"{end_date} 23:59:59")]],
		"skip_auto_attendance": 0
	}
	if filters.employee:
		conditions["employee"] = filters.employee
	
	logs = frappe.get_all(
		"Employee Checkin",
		filters=conditions,
		fields=["employee", "time", "log_type"],
		order_by="time asc",
		limit=0
	)
	
	checkin_map = {}
	for log in logs:
		date_str = str(log.time.date())
		checkin_map.setdefault(log.employee, {}).setdefault(date_str, []).append(log)
	return checkin_map


def get_request_map(filters):
	"""Returns a map of pending attendance requests: { employee: { date: reason } }"""
	start_date, end_date = get_report_date_range(filters)
	
	requests = frappe.get_all(
		"Attendance Request",
		filters={
			"from_date": ["<=", end_date],
			"to_date": [">=", start_date],
			"docstatus": ["<", 2]
		},
		fields=["employee", "from_date", "to_date", "reason"]
	)
	
	request_map = {}
	for r in requests:
		curr = getdate(max(r.from_date, start_date))
		last = getdate(min(r.to_date, end_date))
		while curr <= last:
			date_str = str(curr)
			reason = "Work From Home" if r.reason == "Work From Home" else "Requested"
			request_map.setdefault(r.employee, {})[date_str] = reason
			curr = add_days(curr, 1)
	return request_map


def get_leave_application_map(filters):
	"""Returns a map of pending leave apps: { employee: { date: leave_type } }"""
	start_date, end_date = get_report_date_range(filters)
	
	apps = frappe.get_all(
		"Leave Application",
		filters={
			"from_date": ["<=", end_date],
			"to_date": [">=", start_date],
			"docstatus": ["<", 2],
			"status": ["not in", ["Rejected", "Cancelled"]]
		},
		fields=["employee", "from_date", "to_date", "leave_type"]
	)
	
	leave_app_map = {}
	for a in apps:
		curr = getdate(max(a.from_date, start_date))
		last = getdate(min(a.to_date, end_date))
		while curr <= last:
			leave_app_map.setdefault(a.employee, {})[str(curr)] = a.leave_type
			curr = add_days(curr, 1)
	return leave_app_map


def get_leave_details_map(filters):
	"""Returns a map of leave details: { (employee, date): leave_type }"""
	start_date, end_date = get_report_date_range(filters)
	attendance = frappe.get_all(
		"Attendance",
		filters={
			"attendance_date": ["between", [start_date, end_date]],
			"docstatus": 1,
			"status": "On Leave"
		},
		fields=["employee", "attendance_date", "leave_type"]
	)
	return {(a.employee, str(a.attendance_date)): a.leave_type for a in attendance}


def get_report_date_range(filters):
	if filters.filter_based_on == "Month":
		start_date = getdate(f"{filters.year}-{filters.month}-01")
		end_date = add_days(add_months(start_date, 1), -1)
	else:
		start_date = getdate(filters.start_date)
		end_date = getdate(filters.end_date)
	return start_date, end_date


def get_message() -> str:
	message = ""
	colors = [
		"green", "red", "orange", "#914EE3", "green", "#3187D8", "#878787", "#878787", 
		"#27ae60", "#27ae60", "#3187D8", "#3187D8"
	]

	count = 0
	for status, abbr in status_map.items():
		if abbr == "P(RQ)":
			count += 1
			continue
			
		style = f"border-left: 2px solid {colors[count]};"
		if "(RQ)" in abbr or "(U)" in abbr:
			style += " font-style: italic;"
		
		message += f"""
			<span style='{style} padding-right: 12px; padding-left: 5px; margin-right: 3px;'>
				{_(status)} - {abbr}
			</span>
		"""
		count += 1

	return message


def get_columns(filters: Filters) -> list[dict]:
	columns = []

	if filters.group_by:
		options_mapping = {"Branch": "Branch", "Grade": "Employee Grade", "Department": "Department", "Designation": "Designation"}
		columns.append({"label": _(filters.group_by), "fieldname": frappe.scrub(filters.group_by), "fieldtype": "Link", "options": options_mapping.get(filters.group_by), "width": 120})

	columns.extend([
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 140},
	])

	if filters.summarized_view:
		columns.extend([
			{"label": _("Total Present"), "fieldname": "total_present", "fieldtype": "Float", "width": 110},
			{"label": _("Total Leaves"), "fieldname": "total_leaves", "fieldtype": "Float", "width": 110},
			{"label": _("Total Absent"), "fieldname": "total_absent", "fieldtype": "Float", "width": 110},
			{"label": _("Total Holidays"), "fieldname": "total_holidays", "fieldtype": "Float", "width": 110},
			{"label": _("Pending Req."), "fieldname": "pending_requests", "fieldtype": "Float", "width": 120},
			{"label": _("Unmarked (Logs)"), "fieldname": "unmarked_with_logs", "fieldtype": "Float", "width": 130},
			{"label": _("Unmarked Days"), "fieldname": "unmarked_days", "fieldtype": "Float", "width": 110},
		])

		leave_types = frappe.get_all("Leave Type", pluck="name")
		for leave_type in leave_types:
			columns.append({"label": _(leave_type), "fieldname": frappe.scrub(leave_type), "fieldtype": "Float", "width": 120})

		columns.extend([
			{"label": _("Total Late Entries"), "fieldname": "total_late_entries", "fieldtype": "Float", "width": 110},
			{"label": _("Total Early Exits"), "fieldname": "total_early_exits", "fieldtype": "Float", "width": 110},
		])
	else:
		days = get_columns_for_days(filters)
		columns.extend(days)

	return columns


def get_columns_for_days(filters: Filters) -> list[dict]:
	days = []
	dates = get_dates_in_period(filters)
	for d in dates:
		d = getdate(d)
		days.append({"label": f"{d.day} {d.strftime('%b')} ({day_abbr[d.weekday()]})", "fieldname": d.strftime("%d-%m-%Y"), "fieldtype": "Data", "width": 100})
	return days


def get_dates_in_period(filters: Filters) -> list[str]:
	if filters.filter_based_on == "Month":
		number_of_days = monthrange(cint(filters.year), cint(filters.month))[1]
		return [f"{filters.year}-{filters.month}-{day}" for day in range(1, number_of_days + 1)]
	else:
		return get_date_range(filters.start_date, filters.end_date)


def get_attendance_map(filters: Filters) -> dict:
	attendance_records = get_attendance_records(filters)
	attendance_map = {}

	for record in attendance_records:
		if record.employee not in attendance_map: attendance_map[record.employee] = {}
		current_status = attendance_map[record.employee].get(record.attendance_date)
		if not current_status or STATUS_PRIORITY.get(record.status, 0) > STATUS_PRIORITY.get(current_status, 0):
			attendance_map[record.employee][record.attendance_date] = record.status

	# handle leave without shift
	leaves = frappe.get_all("Attendance", filters={"attendance_date": ["between", get_report_date_range(filters)], "docstatus": 1, "status": "On Leave"}, fields=["employee", "attendance_date"])
	for leave in leaves:
		if leave.employee in attendance_map:
			current_status = attendance_map[leave.employee].get(leave.attendance_date)
			if not current_status or STATUS_PRIORITY.get("On Leave") > STATUS_PRIORITY.get(current_status, 0):
				attendance_map[leave.employee][leave.attendance_date] = "On Leave"
	return attendance_map


def get_attendance_records(filters: Filters) -> list[dict]:
	Attendance = frappe.qb.DocType("Attendance")
	attendance_date_condition = get_date_condition(Attendance.attendance_date, filters)
	status = (frappe.qb.terms.Case().when(((Attendance.status == "Half Day") & (Attendance.half_day_status == "Present")), "Half Day/Other Half Present").when(((Attendance.status == "Half Day") & (Attendance.half_day_status == "Absent")), "Half Day/Other Half Absent").else_(Attendance.status))
	query = (frappe.qb.from_(Attendance).select(Attendance.employee, Attendance.attendance_date, (status).as_("status")).where((Attendance.docstatus == 1) & (Attendance.company.isin(filters.companies)) & (attendance_date_condition)))
	if filters.employee: query = query.where(Attendance.employee == filters.employee)
	query = query.orderby(Attendance.employee, Attendance.attendance_date)
	return query.run(as_dict=1)


def get_date_condition(column: Field, filters: Filters) -> Criterion:
	if filters.filter_based_on == "Month": return (Extract("month", column) == filters.month) & (Extract("year", column) == filters.year)
	else: return (column >= filters.start_date) & (column <= filters.end_date)


def get_employee_related_details(filters: Filters) -> tuple[dict, list]:
	Employee = frappe.qb.DocType("Employee")
	joining_date_condition = get_date_condition(Employee.date_of_joining, filters)
	query = (frappe.qb.from_(Employee).select(Employee.name, Employee.employee_name, Employee.designation, Employee.grade, Employee.department, Employee.branch, Employee.company, Employee.holiday_list, (Employee.date_of_joining).as_("joined_date"), Case().when(joining_date_condition, 1).else_(0).as_("joined_in_current_period")).where(Employee.company.isin(filters.companies)))
	if filters.employee: query = query.where(Employee.name == filters.employee)
	if filters.department and filters.department != "All Departments": query = query.where(Employee.department == filters.department)
	if filters.branch: query = query.where(Employee.branch == filters.branch)
	group_by = filters.group_by
	if group_by: query = query.orderby(group_by.lower())
	employee_details = query.run(as_dict=True)
	group_by_param_values = []
	emp_map = {}
	if group_by:
		group_key = lambda d: "" if d[group_by.lower()] is None else d[group_by.lower()]
		for parameter, employees in groupby(sorted(employee_details, key=group_key), key=group_key):
			group_by_param_values.append(parameter)
			emp_map.setdefault(parameter, frappe._dict())
			for emp in employees: emp_map[parameter][emp.name] = emp
	else:
		for emp in employee_details: emp_map[emp.name] = emp
	return emp_map, group_by_param_values


def get_holiday_map(filters: Filters) -> dict[str, list[dict]]:
	holiday_lists = frappe.db.get_all("Holiday List", pluck="name")
	default_holiday_list = frappe.get_cached_value("Company", filters.company, "default_holiday_list")
	holiday_lists.append(default_holiday_list)
	holiday_map = frappe._dict()
	Holiday = frappe.qb.DocType("Holiday")
	holiday_condition = get_date_condition(Holiday.holiday_date, filters)
	for d in holiday_lists:
		if not d: continue
		holidays = (frappe.qb.from_(Holiday).select(Holiday.holiday_date, Holiday.weekly_off).where((Holiday.parent == d) & (holiday_condition))).run(as_dict=True)
		holiday_map.setdefault(d, holidays)
	return holiday_map


def get_data(filters: Filters, attendance_map: dict, checkin_map: dict = None, leave_details_map: dict = None, request_map: dict = None, leave_app_map: dict = None) -> list[dict]:
	employee_details, group_by_param_values = get_employee_related_details(filters)
	holiday_map = get_holiday_map(filters)
	if filters.group_by:
		data = []
		for parameter in group_by_param_values:
			data.append({frappe.scrub(filters.group_by): parameter})
			rows = get_rows(employee_details[parameter], filters, holiday_map, attendance_map, checkin_map, leave_details_map, request_map, leave_app_map)
			data.extend(rows)
		return data
	else:
		return get_rows(employee_details, filters, holiday_map, attendance_map, checkin_map, leave_details_map, request_map, leave_app_map)


def get_rows(employee_details: dict, filters: Filters, holiday_map: dict, attendance_map: dict, checkin_map: dict = None, leave_details_map: dict = None, request_map: dict = None, leave_app_map: dict = None) -> list[dict]:
	records = []
	default_holiday_list = frappe.get_cached_value("Company", filters.company, "default_holiday_list")
	for employee, details in employee_details.items():
		emp_holiday_list = details.holiday_list or default_holiday_list
		holidays = holiday_map.get(emp_holiday_list)
		emp_checkins = checkin_map.get(employee, {}) if checkin_map else {}
		emp_requests = request_map.get(employee, {}) if request_map else {}
		emp_leave_apps = leave_app_map.get(employee, {}) if leave_app_map else {}

		if filters.summarized_view:
			attendance = get_attendance_status_for_summarized_view(employee, filters, holidays, details.joined_in_current_period, details.joined_date, attendance_map, emp_checkins, emp_requests, emp_leave_apps)
			if not attendance: continue
			row = {"employee": employee, "employee_name": details.employee_name}
			set_defaults_for_summarized_view(filters, row)
			row.update(attendance)
			row.update(get_leave_summary(employee, filters))
			row.update(get_entry_exits_summary(employee, filters))
			records.append(row)
		else:
			status_dict = attendance_map.get(employee, {})
			row = get_attendance_status_for_detailed_view(employee, filters, status_dict, holidays, emp_checkins, leave_details_map, emp_requests, emp_leave_apps)
			row.update({"employee": employee, "employee_name": details.employee_name})
			records.append(row)
	return records


def set_defaults_for_summarized_view(filters, row):
	for entry in get_columns(filters):
		if entry.get("fieldtype") == "Float": row[entry.get("fieldname")] = 0.0


def get_attendance_status_for_summarized_view(employee, filters, holidays, joined_in_current_period, joined_date, attendance_map, emp_checkins, emp_requests, emp_leave_apps) -> dict:
	summary, attendance_days = get_attendance_summary_and_days(employee, filters)
	total_days = get_dates_in_period(filters)
	total_holidays = total_unmarked_days = unmarked_with_logs = pending_requests = 0
	for d in total_days:
		d = getdate(d)
		date_str = str(d)
		if d.day in attendance_days or (joined_in_current_period and d < joined_date): continue
		status = get_holiday_status(d, holidays)
		if status in ["Weekly Off", "Holiday"]: total_holidays += 1
		elif emp_leave_apps.get(date_str) or emp_requests.get(date_str): pending_requests += 1
		elif emp_checkins.get(date_str): unmarked_with_logs += 1
		else: total_unmarked_days += 1
	if not any(summary.values()) and not (total_holidays or total_unmarked_days or unmarked_with_logs or pending_requests): return {}
	return {"total_present": summary.total_present + summary.total_half_days, "total_leaves": summary.total_leaves + summary.total_half_days, "total_absent": summary.total_absent, "total_holidays": total_holidays, "pending_requests": pending_requests, "unmarked_with_logs": unmarked_with_logs, "unmarked_days": total_unmarked_days}


def get_attendance_summary_and_days(employee, filters):
	Attendance = frappe.qb.DocType("Attendance")
	sum_present = Sum(frappe.qb.terms.Case().when(((Attendance.status == "Present") | (Attendance.status == "Work From Home")), 1).else_(0)).as_("total_present")
	sum_absent = Sum(frappe.qb.terms.Case().when(Attendance.status == "Absent", 1).else_(0)).as_("total_absent")
	sum_leave = Sum(frappe.qb.terms.Case().when(Attendance.status == "On Leave", 1).else_(0)).as_("total_leaves")
	sum_half_day = Sum(frappe.qb.terms.Case().when(Attendance.status == "Half Day", 0.5).else_(0)).as_("total_half_days")
	summary = (frappe.qb.from_(Attendance).select(sum_present, sum_absent, sum_leave, sum_half_day).where((Attendance.docstatus == 1) & (Attendance.employee == employee) & (Attendance.company.isin(filters.companies)) & (get_date_condition(Attendance.attendance_date, filters)))).run(as_dict=True)
	days = (frappe.qb.from_(Attendance).select(Extract("day", Attendance.attendance_date).as_("day_of_month")).distinct().where((Attendance.docstatus == 1) & (Attendance.employee == employee) & (Attendance.company.isin(filters.companies)) & (get_date_condition(Attendance.attendance_date, filters)))).run(pluck=True)
	return summary[0], days


def get_leave_abbr(leave_type: str) -> str:
	if not leave_type: return ""
	mapping = {
		"Privilege Leave": "PL",
		"Sick Leave": "SL",
		"Casual Leave": "CL",
		"Compensatory Off": "CO",
		"Compensatory Leave": "CO",
		"Leave Without Pay": "LWP",
		"Maternity Leave": "ML",
		"Paternity Leave": "PTL"
	}
	if leave_type in mapping:
		return mapping[leave_type]
	
	# Fallback: First letter of each word
	return "".join([word[0].upper() for word in str(leave_type).split() if word])

def get_attendance_status_for_detailed_view(employee, filters, status_dict, holidays, emp_checkins, leave_details_map, emp_requests, emp_leave_apps) -> dict:
	total_days = get_dates_in_period(filters)
	row = {"_details": {}, "_status_map": {}}
	duration_view = cint(filters.get("duration_view"))
	for d in total_days:
		d = getdate(d)
		date_str, db_date_str = d.strftime("%d-%m-%Y"), str(d)
		status = status_dict.get(d)
		if status is None and holidays: status = get_holiday_status(d, holidays)
		
		# Audit Priority: Approved > Pending Leave > Pending Att Request > Unmarked Logs
		if not status:
			pending_lt = emp_leave_apps.get(db_date_str)
			if pending_lt: status = "Leave (Requested)"
			else:
				req_reason = emp_requests.get(db_date_str)
				if req_reason: status = "WFH (Requested)" if req_reason == "Work From Home" else "Present (Requested)"
				elif emp_checkins.get(db_date_str): status = "Present (Unmarked)"

		row["_status_map"][date_str] = status
		abbr = status_map.get(status, "")
		if status == "On Leave" and leave_details_map:
			lt = leave_details_map.get((employee, db_date_str))
			if lt: abbr = f"L({get_leave_abbr(lt)})"
		
		tooltip_info = []
		work_duration_str = "0h 00m"
		day_logs = emp_checkins.get(db_date_str, [])
		if day_logs:
			first_in_dt, last_out_dt = day_logs[0].time, day_logs[-1].time
			tooltip_info.extend([f"IN: {first_in_dt.strftime('%H:%M')}", f"OUT: {last_out_dt.strftime('%H:%M')}"])
			work_seconds = 0
			clusters = []
			for log_type, group in groupby(day_logs, key=lambda x: x.log_type): clusters.append((log_type, list(group)))
			for i in range(len(clusters) - 1):
				if clusters[i][0] == "IN" and clusters[i+1][0] == "OUT": work_seconds += (clusters[i+1][1][-1].time - clusters[i][1][0].time).total_seconds()
			if work_seconds <= 0 and status in ["Present", "Work From Home", "Half Day", "Present (Unmarked)", "Present (Requested)", "WFH (Requested)"]:
				work_seconds = (last_out_dt - first_in_dt).total_seconds()
			if work_seconds > 0:
				work_duration_str = f"{int(work_seconds//3600)}h {int((work_seconds%3600)//60):02d}m"
				tooltip_info.append(f"Work: {work_duration_str}")
		
		if status == "On Leave" and leave_details_map:
			lt = leave_details_map.get((employee, db_date_str))
			if lt: tooltip_info.insert(0, f"Leave: {lt}")
		elif status == "Leave (Requested)":
			pending_lt = emp_leave_apps.get(db_date_str)
			if pending_lt:
				abbr = f"L(RQ-{get_leave_abbr(pending_lt)})"
				tooltip_info.insert(0, f"Status: Leave (Requested)\nLeave Type: {pending_lt}")

		if status and "Requested" in str(status) and status != "Leave (Requested)": 
			tooltip_info.insert(0, _("Status: Attendance Request Pending"))
		elif status == "Present (Unmarked)": 
			tooltip_info.insert(0, _("Status: Unmarked (Check-ins Exist)"))

		if tooltip_info: row["_details"][date_str] = "\n".join(tooltip_info)
		active_presence = ["Present", "Work From Home", "Half Day/Other Half Present", "Half Day/Other Half Absent", "Half Day", "Present (Unmarked)", "Present (Requested)", "WFH (Requested)"]
		if duration_view and status in active_presence: row[date_str] = work_duration_str if work_duration_str != "0h 00m" else abbr
		else: row[date_str] = abbr
	return row


def get_holiday_status(holiday_date, holidays) -> str:
	if holidays:
		for holiday in holidays:
			if holiday_date == holiday.get("holiday_date"): return "Weekly Off" if holiday.get("weekly_off") else "Holiday"
	return None


def get_leave_summary(employee, filters) -> dict:
	Attendance = frappe.qb.DocType("Attendance")
	sum_leave_days = Sum(frappe.qb.terms.Case().when(Attendance.status == "Half Day", 0.5).else_(1)).as_("leave_days")
	leave_details = (frappe.qb.from_(Attendance).select(Attendance.leave_type, sum_leave_days).where((Attendance.employee == employee) & (Attendance.docstatus == 1) & (Attendance.company.isin(filters.companies)) & ((Attendance.leave_type.isnotnull()) | (Attendance.leave_type != "")) & (get_date_condition(Attendance.attendance_date, filters))).groupby(Attendance.leave_type)).run(as_dict=True)
	return {frappe.scrub(d.leave_type): d.leave_days for d in leave_details}


def get_entry_exits_summary(employee, filters) -> dict:
	Attendance = frappe.qb.DocType("Attendance")
	entry_exits = (frappe.qb.from_(Attendance).select(Count(frappe.qb.terms.Case().when(Attendance.late_entry == "1", "1")).as_("total_late_entries"), Count(frappe.qb.terms.Case().when(Attendance.early_exit == "1", "1")).as_("total_early_exits")).where((Attendance.docstatus == 1) & (Attendance.employee == employee) & (Attendance.company.isin(filters.companies)) & (get_date_condition(Attendance.attendance_date, filters)))).run(as_dict=True)
	return entry_exits[0]


@frappe.whitelist()
def get_attendance_years() -> str:
	Attendance = frappe.qb.DocType("Attendance")
	year_list = (frappe.qb.from_(Attendance).select(Extract("year", Attendance.attendance_date).as_("year")).distinct()).run(as_dict=True)
	if year_list: year_list.sort(key=lambda d: d.year, reverse=True)
	else: year_list = [frappe._dict({"year": getdate().year})]
	return "\n".join(cstr(entry.year) for entry in year_list)


def get_chart_data(attendance_map, filters) -> dict:
	days = get_columns_for_days(filters)
	labels, absent, present, leave = [], [], [], []
	for day in days:
		labels.append(day["label"])
		a_day = l_day = p_day = 0
		for __, att_dict in attendance_map.items():
			val = att_dict.get(getdate(day["fieldname"], parse_day_first=True))
			if val == "On Leave": l_day += 1
			elif val == "Absent": a_day += 1
			elif val in ["Present", "Work From Home"]: p_day += 1
			elif val == "Half Day": p_day += 0.5; l_day += 0.5
		absent.append(a_day); present.append(p_day); leave.append(l_day)
	return {"data": {"labels": labels, "datasets": [{"name": _("Absent"), "values": absent}, {"name": _("Present"), "values": present}, {"name": _("Leave"), "values": leave}]}, "type": "line", "colors": ["red", "green", "blue"]}
