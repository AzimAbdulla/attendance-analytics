import frappe


@frappe.whitelist(allow_guest=True)
def checkin(employee):
    doc = frappe.get_doc({
        "doctype": "Employee Checkin",
        "employee": employee,
        "log_type": "IN",
        "time": frappe.utils.now_datetime()
    })

    doc.insert(ignore_permissions=True)
    session = frappe.get_doc({
        "doctype": "WFH Session",
        "employee": employee,
        "device_id": employee,
        "session_start": frappe.utils.now_datetime(),
        "last_heartbeat": frappe.utils.now_datetime(),
        "status": "Active"
    })

    session.insert(ignore_permissions=True)



    frappe.db.commit()

    return {
        "status": "success",
        "checkin": doc.name
    }


@frappe.whitelist(allow_guest=True)
def checkout(employee):
    doc = frappe.get_doc({
        "doctype": "Employee Checkin",
        "employee": employee,
        "log_type": "OUT",
        "time": frappe.utils.now_datetime()
    })

    doc.insert(ignore_permissions=True)
    active_sessions = frappe.get_all(
        "WFH Session",
        filters={
            "employee": employee,
            "status": "Active"
        },
        pluck="name"
    )

    for session in active_sessions:
        frappe.db.set_value(
            "WFH Session",
            session,
            {
                "status": "Closed",
                "session_end": frappe.utils.now_datetime()
            }
        )


    
    frappe.db.commit()

    return {
        "status": "success",
        "checkin": doc.name
    }


@frappe.whitelist(allow_guest=True)
def heartbeat(employee):
    current_time = frappe.utils.now_datetime()

    frappe.cache().set_value(
        f"heartbeat_{employee}",
        str(current_time)
    )

    session = frappe.get_all(
        "WFH Session",
        filters={
            "employee": employee,
            "status": "Active"
        },
        limit=1,
        pluck="name"
    )

    if session:
        frappe.db.set_value(
            "WFH Session",
            session[0],
            "last_heartbeat",
            current_time
        )

    frappe.db.commit()

    return {
        "status": "success",
        "employee": employee,
        "heartbeat_time": current_time
    }





@frappe.whitelist(allow_guest=True)
def test():
    return {
        "status": "success",
        "message": "WFH Presence API Working"
    }


@frappe.whitelist(allow_guest=True)
def get_status(employee):
    last_log = frappe.get_all(
        "Employee Checkin",
        filters={"employee": employee},
        fields=["log_type", "time"],
        order_by="time desc",
        limit=1
    )

    if not last_log:
        return {
            "checked_in": False
        }

    return {
        "checked_in": last_log[0].log_type == "IN",
        "last_log_type": last_log[0].log_type,
        "last_log_time": last_log[0].time
    }
