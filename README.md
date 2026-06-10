# 📊 Attendance Analytics & WFH Presence Suite

A high-fidelity attendance intelligence module for **Frappe/ERPNext**. This suite provides advanced auditing, automated performance scoring, and real-time Work From Home (WFH) monitoring, ensuring your workforce data is accurate, actionable, and transparent.

---

## 🚀 Key Modules

### 1. The Audit Matrix (Monthly Attendance Report)
*The ultimate tool for data correction.*
- **Ghost Attendance Detection**: Instantly identifies "missing" records—days where employees have biometric logs but no official attendance document.
- **Dynamic Views**:
    - **Status View**: Traditional attendance markers (P, A, L, WFH).
    - **Duration View**: Replaces markers with actual hours worked (e.g., `8h 45m`).
- **Interactive Heatmap**: Automatically highlights under-performing days in **Red** (< 6h) and high-performing days in **Green** (>= 7h).
- **One-Click Audit**: Click any duration to drill down into the raw biometric punches for that specific employee and day.

### 2. The Scorecard (Performance Report)
*Automated performance ranking and compliance grading.*
- **Dynamic Scoring**: Starts every employee at a base score and applies deductions for late arrivals, severe delays, and absences.
- **Trend Tracking**: Visual arrows (↑/↓) show progress in Rank and Score compared to the previous month.
- **Top 10 Chart**: A built-in dashboard visualizing the most compliant employees in the organization.

### 3. WFH Real-Time Presence
*Monitor remote productivity with precision.*
- **Desktop Agent Integration**: Built-in API endpoints to receive "heartbeats" from a local desktop agent.
- **Auto-Logout Logic**: Automatically marks an `OUT` punch if an agent disconnects for more than 3 minutes, preventing "idle" hours.
- **Live Status**: View active WFH sessions and their last known activity time in real-time.

---

## 🧠 Core Algorithm: Clustered Greedy Duration

Most systems calculate duration as `Last OUT - First IN`, which incorrectly includes lunch breaks and errands. Our custom **Clustered Greedy** algorithm solves this:

1.  **Group**: It clusters consecutive biometric "IN" logs and "OUT" logs.
2.  **Pair**: It greedily pairs an "IN cluster" with the following "OUT cluster."
3.  **Result**: It sums only the time between these pairs, **automatically excluding breaks** where the employee was not actively punched in.
4.  **Fallback**: If logs are incomplete, it intelligently falls back to a Span calculation to ensure the employee still receives credit if they were marked "Present" by HR.

---

## ⚙️ Configuration & Customization

The system is highly flexible via the **Attendance Performance Settings** DocType:
- **Office Logic**: Define your start times, grace periods (e.g., 15 mins), and "severe late" thresholds.
- **Penalty Weights**: Set how many points to deduct for specific events like "Sick Leave" or "Late Arrival."
- **Exclusion Lists**: Prevent specific branches (like a "Remote Only" office) or employment types (like "Interns") from appearing in organization-wide performance rankings.

---

## 🚀 API for Developers

Integrate your custom Desktop Agent using these secure endpoints:

| Endpoint | Action |
| :--- | :--- |
| `attendance_analytics.api.checkin` | Logs an **IN** punch and initiates a tracking session. |
| `attendance_analytics.api.checkout` | Logs an **OUT** punch and closes the tracking session. |
| `attendance_analytics.api.heartbeat` | Updates the session "last seen" time (prevents auto-logout). |
| `attendance_analytics.api.get_status` | Returns the current live status (Checked IN/OUT) for an employee. |

---

## 🛠️ Installation

1. **Download the App**:
   ```bash
   bench get-app https://github.com/AzimAbdulla10/attendance-analytics-soxo.git
   ```
2. **Install on your site**:
   ```bash
   bench --site [your-site-name] install-app attendance_analytics
   ```
3. **Migrate and Clear Cache**:
   ```bash
   bench migrate
   bench clear-cache
   ```

---

## ⚠️ Critical System Requirements

> [!IMPORTANT]
> **Frappe Scheduler Must Be Enabled**
> The real-time WFH monitoring and auto-logout functionality **will not work** if your site's scheduler is paused. 
> To verify and enable, run:
> `bench --site [your-site-name] scheduler resume`

---

## 📄 Maintenance

- **Yearly Updates**: The system uses the `'2026'` holiday list for standard working day calculations. Update the `get_standard_working_days` function in the Python controllers on January 1st each year.
- **Formatting**: Do not change the `format_duration` output string (e.g., `8h 30m`) in Python, as the frontend heatmap relies on this specific format to calculate colors.

---
**License**: MIT  
**Author**: Contributors  
**Repo**: [attendance-analytics-soxo](https://github.com/AzimAbdulla10/attendance-analytics-soxo.git)
