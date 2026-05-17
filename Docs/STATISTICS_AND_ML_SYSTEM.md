# Statistics and Machine Learning System for Pomodoro App

## Overview

This document outlines the comprehensive statistics tracking and machine learning system for the Pomodoro + To-Do application. The system is designed to capture all user productivity events in a single database table, enabling flexible filtering for statistics and providing data for ML models to analyze productivity patterns and suggest optimal study routines.

## Database Schema Design

### Single Table Architecture

The system uses a **single comprehensive table** (`user_statistics`) to capture all productivity events, rather than separate tables for different time periods (daily, weekly, monthly). This approach provides:

- **Flexibility**: Filter and aggregate data in any way needed
- **Scalability**: Single source of truth for all analytics
- **Simplicity**: Easier to maintain and query
- **ML-Ready**: Clean, unified dataset for machine learning models

### user_statistics Table Structure

```sql
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
```

### Field Descriptions

- **id**: Primary key
- **user_id**: Foreign key to users table
- **event_type**: Type of event (see Event Types section)
- **task_id**: Optional reference to related task
- **list_id**: Optional reference to related list
- **timestamp**: Unix timestamp of when the event occurred
- **duration_seconds**: Duration of the event (for sessions, breaks, etc.)
- **break_type**: Type of break ('short_break' or 'long_break')
- **session_number**: Which Pomodoro session in the current set
- **task_content**: Text content of the task (for task-related events)
- **task_completion_time_seconds**: Total time taken to complete a task
- **pomodoro_session_duration**: Duration setting for Pomodoro sessions
- **pomodoro_short_break_duration**: Duration setting for short breaks
- **pomodoro_long_break_duration**: Duration setting for long breaks
- **sessions_completed_in_set**: Number of sessions completed in current set
- **metadata**: JSON field for additional event-specific data
- **created_at**: Database record creation timestamp

## Event Types

### Task-Related Events

1. **task_creation**: When a new task is created
2. **task_completion**: When a task is marked as complete
3. **task_deletion**: When a task is deleted

### Break-Related Events

4. **break_completion**: When a break is completed (not skipped)
5. **break_skip**: When a break is skipped

### Session-Related Events

6. **session_start**: When a Pomodoro session starts
7. **session_end**: When a Pomodoro session ends
8. **session_pause**: When a session is paused
9. **session_resume**: When a paused session is resumed

### List-Related Events

10. **list_creation**: When a new list is created
11. **list_deletion**: When a list is deleted

### Settings Events

12. **settings_change**: When user changes Pomodoro settings

## Data Collection Strategy

### Task Completion Time Tracking

When a task is completed, the system will:

1. Calculate total time spent on the task from `task_time_sessions` table
2. Record the completion event with:
   - `event_type`: 'task_completion'
   - `task_id`: The completed task's ID
   - `task_completion_time_seconds`: Total time spent
   - `task_content`: Task text content
   - `timestamp`: When the task was completed

### Break Tracking

#### Completed Breaks

When a user completes a break (doesn't skip it):

1. Record the break completion event with:
   - `event_type`: 'break_completion'
   - `break_type`: 'short_break' or 'long_break'
   - `duration_seconds`: Actual break duration
   - `session_number`: Current session number in the set
   - `timestamp`: When the break was completed

#### Skipped Breaks

When a user skips a break:

1. Record the break skip event with:
   - `event_type`: 'break_skip'
   - `break_type`: 'short_break' or 'long_break'
   - `duration_seconds`: 0 (since it was skipped)
   - `session_number`: Current session number in the set
   - `timestamp`: When the break was skipped

### Session Tracking

For each Pomodoro session:

1. **Session Start**: Record when user starts a focus session
2. **Session End**: Record when session completes (full duration)
3. **Session Pause**: Record when user pauses mid-session
4. **Session Resume**: Record when user resumes a paused session

Each session event includes:
- Current Pomodoro settings (session duration, break durations)
- Session number in current set
- Actual duration (for end events)

## Statistics Filtering

### Time-Based Filtering

The single table architecture allows flexible time-based filtering:

```sql
-- Daily statistics
SELECT * FROM user_statistics 
WHERE user_id = ? 
  AND timestamp >= strftime('%s', 'now', '-1 day')

-- Weekly statistics  
SELECT * FROM user_statistics 
WHERE user_id = ? 
  AND timestamp >= strftime('%s', 'now', '-7 days')

-- Monthly statistics
SELECT * FROM user_statistics 
WHERE user_id = ? 
  AND timestamp >= strftime('%s', 'now', '-30 days')

-- Custom date range
SELECT * FROM user_statistics 
WHERE user_id = ? 
  AND timestamp >= ? 
  AND timestamp <= ?
```

### Event Type Filtering

```sql
-- Task completions only
SELECT * FROM user_statistics 
WHERE user_id = ? 
  AND event_type = 'task_completion'

-- Break events only
SELECT * FROM user_statistics 
WHERE user_id = ? 
  AND event_type IN ('break_completion', 'break_skip')

-- Session events only
SELECT * FROM user_statistics 
WHERE user_id = ? 
  AND event_type IN ('session_start', 'session_end', 'session_pause', 'session_resume')
```

### Combined Filtering

```sql
-- Completed short breaks in the last week
SELECT * FROM user_statistics 
WHERE user_id = ? 
  AND event_type = 'break_completion'
  AND break_type = 'short_break'
  AND timestamp >= strftime('%s', 'now', '-7 days')

-- Task completions with their completion times
SELECT task_content, task_completion_time_seconds, timestamp
FROM user_statistics 
WHERE user_id = ? 
  AND event_type = 'task_completion'
ORDER BY timestamp DESC
```

## Statistics Metrics

### Task Metrics

- **Average task completion time**: Mean time to complete tasks
- **Task completion rate**: Tasks completed vs. tasks created
- **Task completion time distribution**: Histogram of completion times
- **Tasks per day/week/month**: Count of completed tasks in time period

### Break Metrics

- **Break completion rate**: Completed breaks vs. total breaks
- **Break skip rate**: Skipped breaks vs. total breaks
- **Average break duration**: Mean duration of completed breaks
- **Break type distribution**: Short vs. long break completion rates

### Session Metrics

- **Session completion rate**: Completed sessions vs. started sessions
- **Session pause rate**: Paused sessions vs. total sessions
- **Average session duration**: Mean duration of completed sessions
- **Sessions per day/week/month**: Count of sessions in time period
- **Set completion rate**: Completed 4-session sets vs. started sets

### Productivity Metrics

- **Total focus time**: Sum of all completed session durations
- **Productivity score**: Composite metric based on multiple factors
- **Consistency score**: Variance in daily productivity
- **Optimal session duration**: Most productive session length

## Machine Learning Models

### Model 1: Productivity Categorization (Decision Tree)

**Purpose**: Categorize user productivity into levels from "bad" to "amazing"

**Features**:
- Average task completion time
- Task completion rate
- Break completion rate
- Session completion rate
- Total focus time per day
- Consistency score (variance in daily metrics)
- Break skip rate
- Session pause rate
- Time of day patterns
- Day of week patterns

**Target Classes**:
- Bad (0-20% productivity score)
- Poor (20-40% productivity score)
- Average (40-60% productivity score)
- Good (60-80% productivity score)
- Excellent (80-90% productivity score)
- Amazing (90-100% productivity score)

**Implementation Details**:
- Use scikit-learn DecisionTreeClassifier
- Train on historical user data
- Provide feature importance analysis
- Enable explainability for users

### Model 2: Optimal Routine Suggestion (Regression)

**Purpose**: Predict optimal changes to study routine for maximum productivity

**Features**:
- Current Pomodoro session duration
- Current short break duration
- Current long break duration
- Historical productivity metrics
- Time of day patterns
- Task complexity metrics
- Break completion patterns
- Session completion patterns

**Targets**:
- Optimal session duration (in minutes)
- Optimal short break duration (in minutes)
- Optimal long break duration (in minutes)
- Optimal number of sessions per day
- Optimal time of day for sessions

**Implementation Details**:
- Use scikit-learn regression models (RandomForestRegressor, GradientBoostingRegressor)
- Train on historical user data with productivity as target
- Provide confidence intervals for recommendations
- Enable A/B testing of recommendations

## Implementation Plan

### Phase 1: Data Collection Infrastructure

1. **Create database migration** to add `user_statistics` table
2. **Implement event logging functions** for each event type
3. **Add triggers/hooks** in existing code to log events
4. **Test data collection** with sample data

### Phase 2: Statistics Dashboard

1. **Create statistics API endpoints** for filtering and aggregation
2. **Build frontend dashboard** to display statistics
3. **Implement time-based filtering** (daily/weekly/monthly)
4. **Add visualizations** (charts, graphs, trends)

### Phase 3: ML Model Development

1. **Feature engineering** from collected data
2. **Train productivity categorization model**
3. **Train optimal routine suggestion model**
4. **Implement model serving** API
5. **Add model results to dashboard**

### Phase 4: Optimization and Feedback

1. **Collect user feedback** on ML recommendations
2. **Retrain models** with new data
3. **A/B test** recommendations
4. **Refine metrics** based on user behavior

## Data Privacy and Security

- All statistics data is tied to `user_id` with proper foreign key constraints
- Data is automatically deleted when user account is deleted (CASCADE)
- No personally identifiable information in statistics table
- Timestamps use Unix format for consistency
- Metadata field can store additional context without schema changes

## Performance Considerations

### Database Indexing

The table includes strategic indexes for common query patterns:
- `idx_user_statistics_user_id`: Fast user-specific queries
- `idx_user_statistics_timestamp`: Time-based filtering
- `idx_user_statistics_event_type`: Event type filtering
- `idx_user_statistics_user_timestamp`: Combined user + time queries
- `idx_user_statistics_user_event`: Combined user + event type queries
- `idx_user_statistics_task_id`: Task-specific queries

### Query Optimization

- Use timestamp ranges for time-based filtering
- Filter by user_id first to reduce dataset size
- Use appropriate indexes for event type queries
- Consider materialized views for complex aggregations
- Implement caching for frequently accessed statistics

## Future Enhancements

### Additional Event Types

- **Task modification**: When task content is edited
- **Tag assignment**: When tags are added/removed from tasks
- **List activation**: When user switches active list
- **Goal setting**: When user sets productivity goals
- **Achievement unlock**: When user achieves milestones

### Advanced Analytics

- **Heatmaps**: Productivity patterns by time of day/day of week
- **Trend analysis**: Long-term productivity trends
- **Correlation analysis**: Relationships between different metrics
- **Predictive analytics**: Predict future productivity based on patterns

### ML Model Enhancements

- **Time series forecasting**: Predict future productivity
- **Anomaly detection**: Identify unusual productivity patterns
- **Clustering**: Group similar productivity patterns
- **Reinforcement learning**: Optimize recommendations based on user feedback

## Conclusion

This comprehensive statistics and ML system provides a solid foundation for understanding user productivity patterns and providing actionable insights. The single-table architecture ensures flexibility and simplicity while the modular implementation plan allows for incremental development and testing.
