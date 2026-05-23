import frappe
from attendance_analytics.attendance_analytics.report.monthly_attendance_performance_report.monthly_attendance_performance_report import execute as run_report

@frappe.whitelist()
def get_dashboard_data(filters=None):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)
        
    if not filters:
        now = frappe.utils.now_datetime()
        filters = {
            "month": now.strftime("%m"),
            "year": now.strftime("%Y")
        }
    
    # Get data from the report engine
    columns, data, message, chart = run_report(filters)
    
    # Filter only ranked employees (exclude WFH score 0/None)
    ranked_data = [d for d in data if d.get("rank") is not None]
    
    if not ranked_data:
        return {
            "leaderboard": [],
            "kpis": {
                "highest_score": 0,
                "avg_score": 0,
                "total_ranked": 0
            }
        }
    
    # Calculate KPIs
    highest_score = max(d["final_score"] for d in ranked_data)
    avg_score = sum(d["final_score"] for d in ranked_data) / len(ranked_data)
    
    return {
        "leaderboard": ranked_data,
        "kpis": {
            "highest_score": round(highest_score, 1),
            "avg_score": round(avg_score, 1),
            "total_ranked": len(ranked_data)
        }
    }
