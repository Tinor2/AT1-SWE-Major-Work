-- Migration 001: Add hierarchical task support
-- This migration adds parent-child relationship support to the tasks table

-- Add hierarchical fields to tasks table
ALTER TABLE tasks ADD COLUMN parent_id INTEGER DEFAULT NULL;
ALTER TABLE tasks ADD COLUMN level INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN path TEXT DEFAULT NULL;

-- Add foreign key constraint for parent_id
-- Note: SQLite doesn't support ADD CONSTRAINT directly, so we handle this in application logic

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_level ON tasks(level);
CREATE INDEX IF NOT EXISTS idx_tasks_path ON tasks(path);

-- Initialize existing tasks as root-level tasks
UPDATE tasks SET 
    level = 0, 
    path = CAST(id AS TEXT) 
WHERE parent_id IS NULL;

-- Ensure all tasks have a path value
UPDATE tasks SET path = CAST(id AS TEXT) WHERE path IS NULL;
