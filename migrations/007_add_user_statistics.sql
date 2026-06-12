-- Add user statistics table for comprehensive productivity tracking
-- Migration 007: Create user_statistics table and indexes

-- Create user_statistics table to capture all events for statistics and ML
CREATE TABLE IF NOT EXISTS user_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN (
        'task_completion',
        'break_completion',
        'break_skip',
        'session_start',
        'session_end',
        'session_pause',
        'session_resume',
        'task_creation',
        'task_deletion',
        'list_creation',
        'list_deletion',
        'settings_change'
    )),
    task_id INTEGER,
    list_id INTEGER,
    timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    duration_seconds INTEGER DEFAULT 0,
    break_type TEXT CHECK(break_type IN ('short_break', 'long_break', NULL)),
    session_number INTEGER DEFAULT 0,
    task_content TEXT,
    task_completion_time_seconds INTEGER,
    pomodoro_session_duration INTEGER,
    pomodoro_short_break_duration INTEGER,
    pomodoro_long_break_duration INTEGER,
    sessions_completed_in_set INTEGER,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    FOREIGN KEY (list_id) REFERENCES lists (id) ON DELETE CASCADE
);

-- Create indexes for user_statistics performance
CREATE INDEX IF NOT EXISTS idx_user_statistics_user_id ON user_statistics(user_id);
CREATE INDEX IF NOT EXISTS idx_user_statistics_timestamp ON user_statistics(timestamp);
CREATE INDEX IF NOT EXISTS idx_user_statistics_event_type ON user_statistics(event_type);
CREATE INDEX IF NOT EXISTS idx_user_statistics_user_timestamp ON user_statistics(user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_user_statistics_user_event ON user_statistics(user_id, event_type);
CREATE INDEX IF NOT EXISTS idx_user_statistics_task_id ON user_statistics(task_id);
