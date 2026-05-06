-- Add task time tracking functionality
-- Migration 006: Add task time sessions and total time tracking

-- Create task_time_sessions table to track individual work sessions
CREATE TABLE task_time_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    started_at INTEGER NOT NULL,  -- Unix timestamp for efficiency
    ended_at INTEGER NULL,         -- Unix timestamp (null for active sessions)
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Add total_time_seconds column to tasks table for quick access
ALTER TABLE tasks ADD COLUMN total_time_seconds INTEGER DEFAULT 0;

-- Create indexes for performance
CREATE INDEX idx_task_time_sessions_task_user ON task_time_sessions (task_id, user_id);
CREATE INDEX idx_task_time_sessions_active ON task_time_sessions (user_id, ended_at);

-- Add comment for documentation (SQLite doesn't support real comments in ALTER TABLE)
-- Note: total_time_seconds stores cumulative time in seconds for all completed sessions
