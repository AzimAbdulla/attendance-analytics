# Attendance Analytics & WFH Presence Suite

A high-fidelity attendance intelligence module for **Frappe/ERPNext**. This suite provides advanced auditing, automated performance scoring, and real-time Work From Home (WFH) monitoring, ensuring your workforce data is accurate, actionable, and transparent.

---

## Key Modules & Reports

### 1. The Audit Matrix (Monthly Employee Attendance Report)
*The fundamental tool for data correction and HR compliance.*
- **Ghost Attendance Detection**: Instantly identifies "missing" records—days where employees have biometric logs but no official attendance document.
    - **P(U)**: Present (Unmarked) - Check-ins exist but no attendance doc.
    - **L(RQ)**: Leave (Requested) - Leave application is pending.
- **Dynamic View Toggles**:
    - **Status View**: Shows traditional attendance markers (P, A, L, WFH, WO, H).
    - **Duration View**: Replaces markers with actual hours worked (e.g., `8h 45m`).
- **Interactive Heatmap**: Automatically highlights work intensity:
    - **Green (>= 7h)**: Full productivity.
    - **Yellow (6h - 7h)**: Warning/Short hours.
    - **Red (< 6h)**: Non-compliant/Missing logs.
- **One-Click Audit**: Click any duration to drill down into the raw biometric punches for that specific day.

### 2. The Scorecard (Monthly Attendance Performance Report)
*Automated performance ranking and organizational compliance grading.*
- **Deductive Scoring Engine**: Starts every employee at a base score and applies deductions based on organizational rules.
- **KPI Columns**:
    - **Compliance %**: Intensity of work on days present.
    - **Overall Work Hour %**: Total delivery vs. full contractual month hours.
    - **Late & Severe Late**: Automated counts of punctuality failures.
- **Trend Tracking**: Visual indicators (↑/↓) show progress in Rank and Score compared to the previous month.
- **Executive Dashboard**: A built-in chart visualizing the Top 10 most compliant employees.

### 3. Monthly Work Duration Report (MWDR)
*A day-by-day "Time Sheet" for deep productivity auditing.*
- **Work vs. Break**: Transparently separates productive "in-office" time from break time.
- **Summary Cards**: Displays aggregated Total Hours, Average Daily Hours, and Present Days count.

---

## Core Algorithm: Clustered Greedy Duration

Most systems calculate duration as `Last OUT - First IN`, which incorrectly includes lunch breaks. Our custom **Clustered Greedy** algorithm solves this:

1.  **Clustering**: Groups consecutive biometric "IN" logs into one "IN Cluster" and consecutive "OUT" logs into an "OUT Cluster."
2.  **Pairing**: It greedily pairs an "IN cluster" with the *immediately following* "OUT cluster."
3.  **Calculation**: `Duration = (Last OUT of OUT-cluster) - (First IN of IN-cluster)`.
4.  **Automatic Break Exclusion**: The time between an "OUT Cluster" and the next "IN Cluster" is treated as a break and **subtracted** from the total work time.
5.  **Fallback**: If logs are incomplete (e.g., forgotten punch), it falls back to a simple Span calculation to ensure the employee still receives basic credit if marked "Present" by HR.

---

## Configuration (Attendance Performance Settings)

The system is highly flexible via the **Attendance Performance Settings** DocType:

- **Office Logic**: 
    - `Office Start Time`: The expected clock-in time.
    - `Late Grace Period`: Minutes allowed before penalties trigger (e.g., 15 mins).
    - `Severe Late Threshold`: The time after which a deduction becomes "Severe."
- **Penalty Weights**: 
    - Set specific point deductions for `Absent`, `Half Day`, `Late`, or individual `Leave Types`.
- **Exclusion Logic**: 
    - Exclude specific **Branches** or **Employment Types** (e.g., "Consultants") from organization-wide rankings to keep data clean.

---

## API for Developers (Desktop Agent)

Integrate your custom Desktop Agent using these secure endpoints:

| Endpoint | Action | Params |
| :--- | :--- | :--- |
| `attendance_analytics.api.checkin` | Logs an **IN** punch and initiates a tracking session. | `employee` |
| `attendance_analytics.api.checkout` | Logs an **OUT** punch and closes the tracking session. | `employee` |
| `attendance_analytics.api.heartbeat` | Updates the session "last seen" time. | `employee` |
| `attendance_analytics.api.get_status` | Returns the current live status (Checked IN/OUT). | `employee` |

---

## Data Architecture

- **WFH Session**: Stores real-time tracking data, heartbeat timestamps, and session status (Active/Closed).
- **Employee Checkin**: The standard HRMS DocType used as the source of truth for all calculations.
- **Attendance**: The official record used for payroll integration.

---

## Installation

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

## Critical System Requirements

> [!IMPORTANT]
> **Frappe Scheduler Must Be Enabled**
> The real-time WFH monitoring and auto-logout functionality **will not work** if your site's scheduler is paused. 
> To verify and enable, run:
> `bench --site [your-site-name] scheduler resume`

---

## Maintenance

- **Yearly Updates**: The system uses the `'2026'` holiday list for standard working day calculations. Update the `get_standard_working_days` function in the Python controllers on January 1st each year.
- **Heatmap Formatting**: The frontend heatmap relies on duration strings being formatted strictly as `Xh YYm`. Do not change the `format_duration` function in Python without a corresponding JS update.

---

**Repository**: [attendance-analytics-soxo](https://github.com/AzimAbdulla10/attendance-analytics-soxo.git)
