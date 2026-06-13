# Attendance Analytics & WFH Presence Suite

A high-fidelity attendance intelligence module for **Frappe/ERPNext**. This suite provides advanced auditing, automated performance scoring, and real-time Work From Home (WFH) monitoring, ensuring your workforce data is accurate, actionable, and transparent.

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
- **Interactive Heatmap**: Automatically highlights work intensity (Green >= 7h, Yellow 6h-7h, Red < 6h).
- **One-Click Audit**: Click any duration to drill down into the raw biometric punches for that specific day.

### 2. Productivity Monitoring (The Indicator System)
The Audit Matrix includes a visual correlation between physical presence and actual work output:
- **Blue Dot Indicator (`#2196F3`)**: Appears if the employee has successfully logged work tasks for that day.
- **Red Dot Indicator (`#F44336`)**: Appears if an employee was "Active" (Present, WFH, or has Check-ins) but logged **Zero** tasks.
- **Visuals**: High-visibility 8px vibrant dots with detailed tooltips showing: `📋 Worklogs: [Count] tasks (Total: [X] hrs)`.

### 3. The Scorecard (Monthly Attendance Performance Report)
Automated performance ranking and organizational compliance grading.
- **Deductive Scoring Engine**: Starts every employee at a base score and applies deductions based on organizational rules (Late, Absent, etc.).
- **KPI Columns**:
    - **Compliance %**: Intensity of work on days present.
    - **Overall Work Hour %**: Total delivery vs. full contractual month hours.
    - **Late & Severe Late**: Automated counts of punctuality failures.
- **Trend Tracking**: Visual indicators show progress in Rank and Score compared to the previous month.

---

## Worklogs & Jira Integration

This module allows for a hybrid worklog ecosystem: manual entry in Frappe and automated daily sync from Jira.

### 1. The Worklog DocType
A streamlined document for tracking daily tasks:
- **Auto-Fill**: For manual entries, the system automatically detects the current user and today's date.
- **Lockdown**: Standard employees are prevented from changing the Date or Assignee, ensuring data integrity.
- **Deduplication**: Automated logs from Jira use a unique `JIRA-{Issue}-{WorklogID}` key to prevent duplicate records.

### 2. Automated Jira Sync
A native Python engine that pulls data directly from the Jira API every night at **8:00 PM**.
- **Comment Parsing**: Automatically extracts plain text from Jira's complex Atlassian Document Format (ADF) JSON.
- **Secure Credentials**: API tokens are stored in the server environment (`site_config.json`) rather than the database for maximum security.

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
- **Timeout**: If an agent stops sending signals for more than **3 minutes**, the server automatically creates an **OUT** punch at the time of the last successful heartbeat and closes the session.

---

## 🧠 Core Algorithm: Clustered Greedy Duration

Most systems calculate duration as `Last OUT - First IN`, which incorrectly includes lunch breaks. Our custom **Clustered Greedy** algorithm solves this:
1.  **Group**: It clusters consecutive biometric "IN" logs and "OUT" logs.
2.  **Pair**: It greedily pairs an "IN cluster" with the following "OUT cluster."
3.  **Result**: It sums only the time between these pairs, **automatically excluding breaks**.
4.  **Fallback**: If logs are incomplete, it intelligently falls back to a Span calculation.

---

## Configuration & Security

### 1. Jira API Credentials
Sensitive Jira credentials must be set via the terminal using the following commands:
```bash
bench --site [your-site-name] set-config jira_domain "https://your-domain.atlassian.net"
bench --site [your-site-name] set-config jira_user_email "your-email@example.com"
bench --site [your-site-name] set-config jira_api_token "your-api-token"
```

### 2. Integration Settings UI
The **Jira Integration Settings** DocType in the Frappe UI acts as a simple control panel to toggle the daily sync and monitor the `Last Sync Status`.

### 3. Attendance Performance Settings
Use this DocType to define office timings, grace periods, penalty weights, and organizational exclusion lists.

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
