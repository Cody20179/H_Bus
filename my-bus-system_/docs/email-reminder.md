# Email Reminder Scheduler

This document describes the new automated reservation reminder feature that ships with the back-office service.

## Backend prerequisites

- Python dependency: install pscheduler in the backend runtime:
  `ash
  pip install apscheduler
  `
- Environment variables (the legacy names are respected):
  - Sender_email or SENDER_EMAIL
  - Password_email or SENDER_EMAIL_PASSWORD
  - Optional overrides:
    - RESERVATION_REMINDER_SMTP_HOST (default smtp.gmail.com)
    - RESERVATION_REMINDER_SMTP_PORT (default 465)
    - RESERVATION_REMINDER_TZ (default Asia/Taipei)

## Database schema

Create the supporting tables if they do not exist yet:

`sql
CREATE TABLE email_schedule_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    enabled TINYINT(1) DEFAULT 0,
    hour TINYINT NOT NULL DEFAULT 8,
    minute TINYINT NOT NULL DEFAULT 0,
    timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Taipei',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_run_at DATETIME NULL,
    last_run_status VARCHAR(32) NULL,
    last_error TEXT NULL
);

CREATE TABLE email_reminder_runs (
    run_id INT AUTO_INCREMENT PRIMARY KEY,
    triggered_by VARCHAR(32) NOT NULL DEFAULT 'scheduler',
    status ENUM('running','success','partial','failed','empty') NOT NULL DEFAULT 'running',
    started_at DATETIME NOT NULL,
    finished_at DATETIME NULL,
    total_emails INT NOT NULL DEFAULT 0,
    success_emails INT NOT NULL DEFAULT 0,
    failed_emails INT NOT NULL DEFAULT 0,
    message VARCHAR(255) NULL,
    error_message TEXT NULL
);

CREATE TABLE email_send_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    run_id INT NOT NULL,
    recipient VARCHAR(255) NULL,
    subject VARCHAR(255) NULL,
    status ENUM('success','failed') NOT NULL DEFAULT 'success',
    reservation_count INT NOT NULL DEFAULT 0,
    reservations_json JSON NULL,
    error_message TEXT NULL,
    trigger_source VARCHAR(32) NOT NULL DEFAULT 'scheduler',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reminder_run FOREIGN KEY (run_id)
        REFERENCES email_reminder_runs(run_id) ON DELETE CASCADE
);
`

The backend will create a default row in email_schedule_settings on first run.

## API overview

- GET /api/reservation-reminder/config — fetch current schedule config and summary.
- PUT /api/reservation-reminder/config — update schedule (enabled, hour, minute, 	imezone).
- POST /api/reservation-reminder/run — trigger the reminder job immediately.
- GET /api/reservation-reminder/logs — paginated execution history with delivery details.

All endpoints require an authenticated admin session (Bearer token).

## Front-end usage

A new menu entry "Email Reminder" is available under the admin portal sidebar. The page lets operators:

1. Review the current schedule, next run and last run status.
2. Change the send time/timezone or pause the schedule.
3. Trigger the reminder manually.
4. Inspect detailed delivery logs with per-recipient results.

The UI consumes the endpoints above via emailReminderApi in src/services/api.ts.
