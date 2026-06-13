# Attendance Analytics & WFH Presence Suite

A high-fidelity attendance intelligence module for Frappe/ERPNext. This suite provides advanced auditing, automated performance scoring, and real-time Work From Home (WFH) monitoring, ensuring your workforce data is accurate, actionable, and transparent.

---

## Key Modules & Reports

### 1. The Audit Matrix (Monthly Employee Attendance Report)
The fundamental tool for data correction and HR compliance. It provides a 1-row-per-employee grid that identifies "Ghost Attendance."
- **Ghost Attendance Detection**: Instantly identifies missing records—days where employees have biometric logs but no official attendance document.
    - **P(U)**: Present (Unmarked) - Check-ins exist but no attendance doc.
    - **L(RQ)**: Leave (Requested) - Leave application is pending.
- **Dynamic View Toggles**:
    - **Status View**: Shows traditional attendance markers (P, A, L, WFH, WO, H).
    - **Duration View**: Replaces markers with actual hours worked (e.g., 8h 45m).
- **Interactive Heatmap**: Automatically highlights work intensity:
    - **Green (>= 7h)**: Full productivity.
    - **Yellow (6h - 7h)**: Warning/Short hours.
    - **Red (< 6h)**: Non-compliant/Missing logs.
- **One-Click Audit**: Click any duration to drill down into the raw biometric punches for that specific day.

### 2. The Scorecard (Monthly Attendance Performance Report)
Automated performance ranking and organizational compliance grading.
- **Deductive Scoring Engine**: Starts every employee at a base score and applies deductions based on organizational rules (Late, Absent, etc.).
- **KPI Columns**:
    - **Compliance %**: Intensity of work on days present.
    - **Overall Work Hour %**: Total delivery vs. full contractual month hours.
    - **Late & Severe Late**: Automated counts of punctuality failures.
- **Trend Tracking**: Visual indicators show progress in Rank and Score compared to the previous month.
- **Executive Dashboard**: A built-in chart visualizing the Top 10 most compliant employees.

---

## Worklogs & Jira Integration

This module allows for a hybrid worklog ecosystem: manual entry in Frappe and automated daily sync from Jira.

### 1. The Worklog DocType
A streamlined 6-field document for tracking daily tasks:
- **Date**: Auto-fills to today.
- **Assignee**: Link to official Employee record (Auto-filled and locked for employees).
- **Priority**: Select field matching Jira priorities.
- **Task**: The title or ID of the work performed.
- **Description**: Detailed multi-line comments.
- **Status**: The current lifecycle stage of the task.

### 2. Automated Jira Sync
A native Python engine that pulls data directly from the Jira API every night.
- **Schedule**: Runs automatically at **8:00 PM** daily.
- **Deduplication**: Uses a unique `JIRA-{Issue}-{WorklogID}` key to ensure logs are never duplicated if synced multiple times.
- **Comment Parsing**: Automatically extracts plain text from Jira's complex Atlassian Document Format (ADF) JSON.

### 3. Employee Mapping
Because Jira often hides user emails, the system uses a **Jira Employee Mapping** table to link Jira `accountId` strings to Frappe `Employee` records with 100% accuracy.

---

## WFH Real-Time Presence

Monitor remote productivity by connecting a desktop agent to Frappe.

### 1. Desktop Agent Integration
The app exposes secure API endpoints for a local machine agent to communicate with the server.
- **API Base**: `/api/method/attendance_analytics.api.[method]`
- **Methods**: `checkin`, `checkout`, `heartbeat`, `get_status`.

### 2. Heartbeat & Auto-Logout
To prevent "idle time" being logged as work, the system requires a constant signal (heartbeat) from the machine.
- **Monitor**: A background task runs every 1 minute.
- **Timeout**: If an agent stops sending signals for more than **3 minutes**, the server automatically creates an **OUT** punch and closes the session.

---

## Core Algorithm: Clustered Greedy Duration

Most systems calculate duration as `Last OUT - First IN`, which incorrectly includes lunch breaks. Our custom **Clustered Greedy** algorithm solves this:
1.  **Group**: It clusters consecutive biometric "IN" logs and "OUT" logs.
2.  **Pair**: It greedily pairs an "IN cluster" with the following "OUT cluster."
3.  **Result**: It sums only the time between these pairs, **automatically excluding breaks**.
4.  **Fallback**: If logs are incomplete, it intelligently falls back to a Span calculation.

---

## Configuration (Attendance Performance Settings)

The system is highly flexible via the **Attendance Performance Settings** DocType:
- **Office Logic**: Define your start times, grace periods, and "severe late" thresholds.
- **Penalty Weights**: Set specific point deductions for Absent, Half Day, or individual Leave Types.
- **Exclusion Lists**: Hide specific Branches or Employment Types from organization-wide rankings.

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
3. **Migrate**:
   ```bash
   bench migrate
   ```

---

## Critical System Requirements

> [!IMPORTANT]
> **Frappe Scheduler Must Be Enabled**
> The real-time WFH monitoring, auto-logout, and 8 PM Jira Sync **will not work** if your site's scheduler is paused. 
> To verify and enable, run:
> `bench --site [your-site-name] scheduler resume`

---
**License**: MIT  
**Author**: Contributors  
**Repository**: [attendance-analytics-soxo](https://github.com/AzimAbdulla10/attendance-analytics-soxo.git)
