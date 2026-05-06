-- Migration script to add user_tags table
-- Run this to add the new table to existing databases

CREATE TABLE IF NOT EXISTS user_tags (
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

-- Create index for user_tags table
CREATE INDEX IF NOT EXISTS idx_user_tags_user_id ON user_tags(user_id);

-- Insert default tags for existing users
INSERT OR IGNORE INTO user_tags (user_id, color_hex, color_name, position)
SELECT 
    id as user_id,
    '#ff5252' as color_hex,
    'Red' as color_name,
    0 as position
FROM users;

INSERT OR IGNORE INTO user_tags (user_id, color_hex, color_name, position)
SELECT 
    id as user_id,
    '#ff9800' as color_hex,
    'Orange' as color_name,
    1 as position
FROM users;

INSERT OR IGNORE INTO user_tags (user_id, color_hex, color_name, position)
SELECT 
    id as user_id,
    '#ffeb3b' as color_hex,
    'Yellow' as color_name,
    2 as position
FROM users;

INSERT OR IGNORE INTO user_tags (user_id, color_hex, color_name, position)
SELECT 
    id as user_id,
    '#4caf50' as color_hex,
    'Green' as color_name,
    3 as position
FROM users;

INSERT OR IGNORE INTO user_tags (user_id, color_hex, color_name, position)
SELECT 
    id as user_id,
    '#00bcd4' as color_hex,
    'Cyan' as color_name,
    4 as position
FROM users;

INSERT OR IGNORE INTO user_tags (user_id, color_hex, color_name, position)
SELECT 
    id as user_id,
    '#3f51b5' as color_hex,
    'Indigo' as color_name,
    5 as position
FROM users;

INSERT OR IGNORE INTO user_tags (user_id, color_hex, color_name, position)
SELECT 
    id as user_id,
    '#9c27b0' as color_hex,
    'Purple' as color_name,
    6 as position
FROM users;

INSERT OR IGNORE INTO user_tags (user_id, color_hex, color_name, position)
SELECT 
    id as user_id,
    '#795548' as color_hex,
    'Brown' as color_name,
    7 as position
FROM users;
