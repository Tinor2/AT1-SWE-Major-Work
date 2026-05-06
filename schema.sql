-- SQL schema for Pomodoro + To-Do App

-- Drop tables if they exist
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

-- Note: Default list insertion removed since lists now require a user_id
