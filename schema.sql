-- SQL schema for Pomodoro + To-Do App

-- Drop tables if they exist
DROP TABLE IF EXISTS user_statistics;
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS lists;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS user_tags;

-- Create users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Create lists table
CREATE TABLE lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT 0,
    pomo_session INTEGER DEFAULT 25,
    pomo_short_break INTEGER DEFAULT 5,
    pomo_long_break INTEGER DEFAULT 15,
    pomo_current_time INTEGER DEFAULT 0,
    -- Timer state management
    timer_state TEXT DEFAULT 'idle' CHECK(timer_state IN ('idle', 'session', 'short_break', 'long_break', 'paused')),
    current_phase TEXT DEFAULT NULL CHECK(current_phase IN ('session', 'short_break', 'long_break')),
    timer_remaining INTEGER DEFAULT 0,
    sessions_completed INTEGER DEFAULT 0,
    timer_started_at TIMESTAMP NULL,
    timer_last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    UNIQUE(user_id, name)
);

-- Create tasks table
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    is_done BOOLEAN DEFAULT 0,
    tags TEXT DEFAULT '',
    position INTEGER DEFAULT 0,
    parent_id INTEGER DEFAULT NULL,
    level INTEGER DEFAULT 0,
    path TEXT DEFAULT NULL,
    total_time_seconds INTEGER DEFAULT 0,
    number_of_full_breaks INTEGER DEFAULT 0,
    number_of_skipped_breaks INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (list_id) REFERENCES lists (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES tasks (id) ON DELETE CASCADE
);

-- Create user_tags table for customizable tag management
CREATE TABLE user_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    color_hex TEXT NOT NULL,
    color_name TEXT,
    position INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    UNIQUE(user_id, color_hex)
);

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

-- Create an index on list_id for faster queries
CREATE INDEX idx_tasks_list_id ON tasks(list_id);

-- Create an index on user_id for faster queries
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_lists_user_id ON lists(user_id);
CREATE INDEX idx_user_tags_user_id ON user_tags(user_id);

-- Create indexes for hierarchical queries
CREATE INDEX idx_tasks_parent_id ON tasks(parent_id);
CREATE INDEX idx_tasks_level ON tasks(level);
CREATE INDEX idx_tasks_path ON tasks(path);

-- Create indexes for task_time_sessions performance
CREATE INDEX idx_task_time_sessions_task_user ON task_time_sessions (task_id, user_id);
CREATE INDEX idx_task_time_sessions_active ON task_time_sessions (user_id, ended_at);

-- Create user_statistics table for comprehensive productivity tracking
-- This single table captures ALL events for statistics and ML analysis
CREATE TABLE user_statistics (
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
CREATE INDEX idx_user_statistics_user_id ON user_statistics(user_id);
CREATE INDEX idx_user_statistics_timestamp ON user_statistics(timestamp);
CREATE INDEX idx_user_statistics_event_type ON user_statistics(event_type);
CREATE INDEX idx_user_statistics_user_timestamp ON user_statistics(user_id, timestamp);
CREATE INDEX idx_user_statistics_user_event ON user_statistics(user_id, event_type);
CREATE INDEX idx_user_statistics_task_id ON user_statistics(task_id);

-- Note: Default list insertion removed since lists now require a user_id
