-- Add current_phase column to preserve phase context when timer is paused
-- Migration: 003_add_current_phase.sql
-- Purpose: Fix pause/reset button issues by storing underlying phase information

ALTER TABLE lists 
ADD COLUMN current_phase TEXT 
CHECK(current_phase IN ('session', 'short_break', 'long_break')) 
DEFAULT NULL;

-- Add comment for clarity (SQLite doesn't support COMMENT ON COLUMN, but this documents intent)
-- current_phase: Stores the actual timer phase when timer_state is 'paused'
-- This allows resume operations to know what phase to restore without guessing
