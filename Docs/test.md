"""Trained ML models directory."""
Here is the updated detailed plan, incorporating your clarifications:

# Statistics and Machine Learning System Implementation Plan

## Overview

This document outlines the detailed plan to complete the implementation of the statistics tracking and machine learning system for the Pomodoro + To-Do application, building upon the existing schema, ML models, and analytics UI. The primary focus is to finalize event logging to ensure the ML models have the necessary data for accurate productivity analysis and routine suggestions.

## Implementation Status Summary (Current)

*   **Implemented**:
    *   **ML Backend (Phase 3)**: All necessary ML files (`trainer.py`, `predictor.py`, `scheduler.py`) are present and correctly implemented. The `pomodoro/__init__.py` modification to start the scheduler is in place. The `pomodoro/routes/routine_suggestion.py` route file is correctly updated with the prediction and retraining endpoints.
    *   **Frontend (Phase 4)**: The "Projected Performance" panel in `pomodoro/templates/analytics/index.html` is fully implemented with the correct HTML, CSS, and JavaScript.
    *   **Database Schema**: The `user_statistics` table and all mentioned indexes are correctly set up in the database.

*   **Partially Implemented/Missing**:
    *   **Phase 1 (Event Logging)**: This is the critical missing piece. The `_log_event` helper function is defined, but the crucial calls to log timer-related events within the `pomodoro/routes/timer.py` route handlers are **missing**. While task and list creation/deletion are logged, timer events are not, which is a prerequisite for the ML models to function with real data.

## Plan to Finalize Setup

### 1. Finish Timer Event Logging (`pomodoro/routes/timer.py`)

The core of the remaining work is to correctly log all timer-related events into the `user_statistics` table.

*   **Helper Function**: The `_log_event` helper function is already defined.
*   **Event Types and Key Fields to Log**:
    *   **`start_timer` (idle → session)**: Log `session_start` with `session_number` (current session + 1), `pomodoro_session_duration`.
    *   **`start_timer` (paused → running)**: Log `session_resume` with `duration_seconds` (elapsed before pause).
    *   **`pause_timer`**: Log `session_pause` with `duration_seconds` (time spent before pause).
    *   **`skip_timer` (from session)**: Log `session_end` with `duration_seconds` (actual time spent in session) and `sessions_completed_in_set`. A "skipped session" is a session that was not allowed to finish naturally (user manually ended it).
    *   **`skip_timer` (from break)**: Log `break_skip` with `break_type` (`short_break` / `long_break`).
    *   **Natural phase completion (client calls `/timer/skip` after countdown)**:
        *   If session completed naturally: Log `session_end` with `duration_seconds` (full session duration) and `sessions_completed_in_set`. A "completed session" is a session that was allowed to finish naturally, without skipping.
        *   If break completed naturally: Log `break_completion` with `break_type` and `duration_seconds` (full break duration).
    *   **`reset_sets`**: Log `settings_change` with `metadata: {"action": "reset_sets"}`.
*   **Important**: Ensure there is no double-logging when the client auto-calls `/timer/skip` after a countdown completes, as the server-side logic already handles phase advancement.

### 2. Audit Task and List Logging (`pomodoro/routes/tasks.py`, `pomodoro/routes/lists.py`)

*   **Confirmation**:
    *   Confirm `task_creation` in `add_task`.
    *   Confirm `task_completion` in `toggle_task` (when marking done).
    *   Confirm `task_deletion` in `delete_task`.
    *   Confirm `list_creation` in `create` (for lists).
    *   Confirm `list_deletion` in `delete_list`.
*   **Scope**: As per user instruction, there is **no need** to log task edits, tag updates, or hierarchy changes for this system.

### 3. Verify Event Semantics

*   **Completed Session**: A session that was allowed to finish naturally, without the user manually skipping it.
*   **Skipped Session**: A session that was not allowed to finish naturally; the user manually triggered its end.
*   **Completed Break**: A break that completed its full duration without being skipped.
*   **Skipped Break**: A break that the user manually skipped before its duration was complete.
*   Ensure the server's timer state transitions (`idle`, `session`, `short_break`, `long_break`, `paused`) accurately map to the logged `event_type` and associated data.
*   Verify that `duration_seconds` accurately reflects the time spent in a phase before a pause, skip, or natural end.

### 4. SQL Schema Usage Validation

*   Confirm that the data being inserted into `user_statistics` for all event types aligns with the table's column definitions.
*   Ensure proper handling of nullable fields (e.g., `task_id`, `list_id`, `break_type`) in `_log_event` calls.
*   If `metadata` is used, ensure it's stored as a JSON string.

### 5. Final Analytics Backend Validation (`models/analytics.py`)

*   Review `models/analytics.py` to confirm that it correctly queries the `user_statistics` table to generate:
    *   Summary statistics (focus time, session counts, task completion rates).
    *   The event log on the analytics page.
    *   Daily focus time chart data.
    *   7/30/90-day filtering for all relevant metrics.
*   Ensure the analytics page gracefully handles scenarios where `user_statistics` might be empty or contain limited data, avoiding errors.

### 6. ML Code Robustness (`pomodoro/ml/trainer.py`, `pomodoro/ml/predictor.py`)

*   **`trainer.py`**:
    *   Verify robust handling of low-data scenarios (fewer than 10 real samples), ensuring synthetic data fallback prevents training errors.
    *   Confirm that model persistence paths (`pomodoro/ml/models/<user_id>/`) are created reliably.
    *   Ensure training does not crash due to malformed historical data from `user_statistics`.
*   **`predictor.py`**:
    *   Confirm `predict_for_user` gracefully handles cases with missing model files or when `compute_features_for_user` returns incomplete data.
    *   Verify the response JSON precisely matches the frontend expectations, including `band`, `motivational`, `factors`, `is_synthetic`, etc.
    *   Ensure the displayed band labels and the `is_synthetic` flag are accurate.

### 7. Scheduler Behavior (`pomodoro/ml/scheduler.py`)

*   Confirm that the `start_scheduler` function in `pomodoro/__init__.py` is called only once on app startup to avoid duplicate threads.
*   Verify the scheduler's logic to retrain models only for active users with recent activity and at the specified `RETRAIN_INTERVAL_SECONDS`.

### 8. Frontend Review (`pomodoro/templates/analytics/index.html`, `pomodoro/static/css/analytics.css`)

*   **`index.html`**:
    *   Confirm the "Projected Performance" panel dynamically updates with data fetched from the `/api/productivity/prediction` endpoint.
    *   Verify that loading, error, and synthetic data states are displayed correctly.
    *   Ensure the "Refresh" button triggers a model retraining (`/api/productivity/retrain`) and updates the panel.
    *   Confirm auto-refresh behavior without conflicts.
*   **`analytics.css`**: Verify that the styling for the "Projected Performance" panel is correct and responsive.

### 9. End-to-End Verification

*   **Simulated User Flow**:
    1.  Log in as a user.
    2.  Create a new list.
    3.  Add a few tasks.
    4.  Start a Pomodoro session, let it run for a while, pause it, resume it, and finally let it complete naturally.
    5.  Start another session and manually skip it.
    6.  Take a short break, let it complete.
    7.  Take another break, but skip it.
    8.  Mark a task as completed.
    9.  Reset Pomodoro sets.
    10. Create and delete a list.
*   **Database Check**: After performing the above actions, use an SQL client to query `user_statistics` and verify that all expected events have been logged with accurate data (`event_type`, `timestamp`, `duration_seconds`, `task_id`, `list_id`, `break_type`, `session_number`, `task_content`, `task_completion_time_seconds`, `pomodoro_*_duration`, `sessions_completed_in_set`, `metadata`).
*   **Analytics Page Check**: Navigate to the analytics page and confirm:
    *   The "Projected Performance" panel displays a productivity band, motivational message, and factors.
    *   The "Event log" panel shows the newly recorded events.
    *   Summary statistics and charts reflect the simulated activity.
    *   Click the "Refresh" button on the "Projected Performance" panel and observe it retraining and updating.

### 10. Regression Testing (If Applicable)

*   If unit or integration tests exist for timer, task, or list functionalities, ensure they still pass after implementing the logging.
*   Consider adding new, focused tests for the `_log_event` calls, particularly for the timer routes, to verify event data accuracy.

---

This detailed plan, incorporating your clarifications, provides a clear roadmap to finalize the statistics and ML system.