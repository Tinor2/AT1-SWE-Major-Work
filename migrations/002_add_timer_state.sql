-- Migration 002: Add Timer State Columns to Lists Table
-- This migration adds timer state management columns to the existing lists table
-- Run this in production to add timer functionality without dropping existing data

-- Add timer state column with CHECK constraint
ALTER TABLE lists ADD COLUMN timer_state TEXT DEFAULT 'idle' CHECK(timer_state IN ('idle', 'session', 'short_break', 'long_break', 'paused'));

-- Add timer remaining time column
ALTER TABLE lists ADD COLUMN timer_remaining INTEGER DEFAULT 0;

-- Add sessions completed counter
ALTER TABLE lists ADD COLUMN sessions_completed INTEGER DEFAULT 0;

-- Add timer start timestamp (NULL when timer is idle)
ALTER TABLE lists ADD COLUMN timer_started_at TIMESTAMP NULL;

-- Add timer last updated timestamp for synchronization
ALTER TABLE lists ADD COLUMN timer_last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Update existing rows to have proper default values
UPDATE lists SET timer_state = 'idle' WHERE timer_state IS NULL;
UPDATE lists SET timer_remaining = 0 WHERE timer_remaining IS NULL;
UPDATE lists SET sessions_completed = 0 WHERE sessions_completed IS NULL;
UPDATE lists SET timer_last_updated = CURRENT_TIMESTAMP WHERE timer_last_updated IS NULL;
